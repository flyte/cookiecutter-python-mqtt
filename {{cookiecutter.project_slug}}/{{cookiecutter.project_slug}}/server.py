import argparse
import logging
import yaml
import sys
import socket
from time import sleep

import paho.mqtt.client as mqtt
import cerberus

from {{ cookiecutter.project_slug }} import CONFIG_SCHEMA


LOG_LEVEL_MAP = {
    mqtt.MQTT_LOG_INFO: logging.INFO,
    mqtt.MQTT_LOG_NOTICE: logging.INFO,
    mqtt.MQTT_LOG_WARNING: logging.WARNING,
    mqtt.MQTT_LOG_ERR: logging.ERROR,
    mqtt.MQTT_LOG_DEBUG: logging.DEBUG
}
RECONNECT_DELAY_SECS = 5

_LOG = logging.getLogger(__name__)
_LOG.addHandler(logging.StreamHandler())
_LOG.setLevel(logging.DEBUG)


class ConfigValidator(cerberus.Validator):
    '''
    Cerberus Validator containing function(s) for use with validating or
    coercing values relevant to the {{ cookiecutter.project_slug }} project.
    '''

    @staticmethod
    def _normalize_coerce_rstrip_slash(value):
        '''
        Strip forward slashes from the end of the string.
        :param value: String to strip forward slashes from
        :type value: str
        :return: String without forward slashes on the end
        :rtype: str
        '''
        return value.rstrip('/')

    @staticmethod
    def _normalize_coerce_tostring(value):
        '''
        Convert value to string.
        :param value: Value to convert
        :return: Value represented as a string.
        :rtype: str
        '''
        return str(value)


def on_log(client, userdata, level, buf):
    '''
    Called when MQTT client wishes to log something.
    :param client: MQTT client instance
    :param userdata: Any user data set in the client
    :param level: MQTT log level
    :param buf: The log message buffer
    :return: None
    :rtype: NoneType
    '''
    _LOG.log(LOG_LEVEL_MAP[level], 'MQTT client: %s' % buf)


def init_mqtt(config):
    '''
    Configure MQTT client.
    :param config: Validated config dict containing MQTT connection details
    :type config: dict
    :return: Connected and initialised MQTT client
    :rtype: paho.mqtt.client.Client
    '''
    topic_prefix = config['topic_prefix']
    protocol = mqtt.MQTTv311
    if config['protocol'] == '3.1':
        protocol = mqtt.MQTTv31

    # https://stackoverflow.com/questions/45774538/what-is-the-maximum-length-of-client-id-in-mqtt
    # TLDR: Soft limit of 23, but we needn't truncate it on our end.
    client_id = config['client_id']
    if not client_id:
        client_id = "pi-mqtt-gpio-%s" % sha1(
            topic_prefix.encode('utf8')).hexdigest()

    client = mqtt.Client(
        client_id=client_id, protocol=protocol, clean_session=False)

    if config['user'] and config['password']:
        client.username_pw_set(config['user'], config['password'])

    # Set last will and testament (LWT)
    status_topic = '%s/%s' % (topic_prefix, config['status_topic'])
    client.will_set(
        status_topic,
        payload=config['status_payload_dead'],
        qos=1,
        retain=True)
    _LOG.debug(
        'Last will set on %r as %r.',
        status_topic,
        config['status_payload_dead'])

    # Set TLS options
    tls_enabled = config.get("tls", {}).get("enabled")
    if tls_enabled:
        tls_config = config["tls"]
        tls_kwargs = dict(
            ca_certs=tls_config.get("ca_certs"),
            certfile=tls_config.get("certfile"),
            keyfile=tls_config.get("keyfile"),
            ciphers=tls_config.get("ciphers")
        )
        try:
            tls_kwargs["cert_reqs"] = getattr(ssl, tls_config["cert_reqs"])
        except KeyError:
            pass
        try:
            tls_kwargs["tls_version"] = getattr(ssl, tls_config["tls_version"])
        except KeyError:
            pass

        client.tls_set(**tls_kwargs)
        client.tls_insecure_set(tls_config["insecure"])

    def on_conn(client, userdata, flags, rc):
        '''
        On connection to MQTT, subscribe to the relevant topics.
        :param client: Connected MQTT client instance
        :type client: paho.mqtt.client.Client
        :param userdata: User data
        :param flags: Response flags from the broker
        :type flags: dict
        :param rc: Response code from the broker
        :type rc: int
        :return: None
        :rtype: NoneType
        '''
        if rc == 0:
            _LOG.info(
                'Connected to the MQTT broker with protocol v%s.',
                config['protocol'])

            # TODO: Subscribe to topics here

            client.publish(
                status_topic,
                config['status_payload_running'],
                qos=1,
                retain=True)
        elif rc == 1:
            _LOG.fatal(
                'Incorrect protocol version used to connect to MQTT broker.')
            sys.exit(1)
        elif rc == 2:
            _LOG.fatal(
                'Invalid client identifier used to connect to MQTT broker.')
            sys.exit(1)
        elif rc == 3:
            _LOG.warning('MQTT broker unavailable. Retrying in %s secs...')
            sleep(RECONNECT_DELAY_SECS)
            client.reconnect()
        elif rc == 4:
            _LOG.fatal(
                'Bad username or password used to connect to MQTT broker.')
            sys.exit(1)
        elif rc == 5:
            _LOG.fatal(
                'Not authorised to connect to MQTT broker.')
            sys.exit(1)

    def on_msg(client, userdata, msg):
        """
        On reception of MQTT message, set the relevant output to a new value.
        :param client: Connected MQTT client instance
        :type client: paho.mqtt.client.Client
        :param userdata: User data (any data type)
        :param msg: Received message instance
        :type msg: paho.mqtt.client.MQTTMessage
        :return: None
        :rtype: NoneType
        """
        try:
            _LOG.info(
                "Received message on topic %r: %r", msg.topic, msg.payload)
            if msg.topic == 'your_topic_here':
                # TODO: Handle incoming messages here
                pass
            else:
                _LOG.warning("Unhandled topic %r.", msg.topic)
        except InvalidPayload as exc:
            _LOG.warning("Invalid payload on received MQTT message: %s" % exc)
        except Exception:
            _LOG.exception("Exception while handling received MQTT message:")

    client.on_connect = on_conn
    client.on_log = on_log
    client.on_message = on_msg

    return client


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('config')
    args = p.parse_args()

    with open(args.config) as f:
        config = yaml.load(f)
    validator = ConfigValidator(CONFIG_SCHEMA)
    if not validator.validate(config):
        _LOG.error(
            'Config did not validate:\n%s',
            yaml.dump(validator.errors))
        sys.exit(1)
    config = validator.normalized(config)

    client = init_mqtt(config['mqtt'])

    try:
        client.connect(config['mqtt']['host'], config['mqtt']['port'], 60)
    except socket.error as err:
        _LOG.fatal('Unable to connect to MQTT server: %s' % err)
        sys.exit(1)
    client.loop_start()

    topic_prefix = config['mqtt']['topic_prefix']
    try:
        while True:
            # TODO: Do something in main loop
            sleep(0.01)
    except KeyboardInterrupt:
        print('')
    finally:
        msg_info = client.publish(
            '%s/%s' % (topic_prefix, config['mqtt']['status_topic']),
            config['mqtt']['status_payload_stopped'], qos=1, retain=True)
        msg_info.wait_for_publish()

        client.disconnect()
        client.loop_forever()
