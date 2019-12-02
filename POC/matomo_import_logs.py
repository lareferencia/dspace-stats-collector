#!/usr/bin/python
#
# Matomo - free/libre analytics platform
#
# @license https://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
# @version $Id$
#
# Requires Python 2.6 or 2.7
#

import sys


if sys.version_info[0] != 2:
    print('The log importer currently does not work with Python 3 (or higher)')
    print('Please use Python 2.6 or 2.7')
    sys.exit(1)

import bz2
import datetime
import gzip
import httplib
import inspect
import itertools
import logging
import os
import os.path
import Queue
import re
import sys
import threading
import time
import urllib
import urllib2
import urlparse
import traceback
import socket
import textwrap
import yaml

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        if sys.version_info < (2, 6):
            print >> sys.stderr, 'simplejson (http://pypi.python.org/pypi/simplejson/) is required.'
            sys.exit(1)



##
## Constants.
##

MATOMO_DEFAULT_MAX_ATTEMPTS = 3
MATOMO_DEFAULT_DELAY_AFTER_FAILURE = 10
DEFAULT_SOCKET_TIMEOUT = 300

##
## Formats.
##

class BaseFormatException(Exception): pass

class BaseFormat(object):
    def __init__(self, name):
        self.name = name
        self.regex = None
        self.date_format = '%d/%b/%Y:%H:%M:%S'

    def check_format(self, file):
        line = file.readline()
        try:
            file.seek(0)
        except IOError:
            pass

        return self.check_format_line(line)

    def check_format_line(self, line):
        return False

class JsonFormat(BaseFormat):
    def __init__(self, name):
        super(JsonFormat, self).__init__(name)
        self.json = None
        self.date_format = '%Y-%m-%dT%H:%M:%S'

    def check_format_line(self, line):
        try:
            self.json = json.loads(line)
            return True
        except:
            return False

    def match(self, line):
        try:
            # nginx outputs malformed JSON w/ hex escapes when confronted w/ non-UTF input. we have to
            # workaround this by converting hex escapes in strings to unicode escapes. the conversion is naive,
            # so it does not take into account the string's actual encoding (which we don't have access to).
            line = line.replace('\\x', '\\u00')

            self.json = json.loads(line)
            return self
        except:
            self.json = None
            return None

    def get(self, key):
        # Some ugly patchs ...
        if key == 'generation_time_milli':
            self.json[key] =  int(float(self.json[key]) * 1000)
        # Patch date format ISO 8601
        elif key == 'date':
            tz = self.json[key][19:]
            self.json['timezone'] = tz.replace(':', '')
            self.json[key] = self.json[key][:19]

        try:
            return self.json[key]
        except KeyError:
            raise BaseFormatException()

    def get_all(self,):
        return self.json

    def remove_ignored_groups(self, groups):
        for group in groups:
            del self.json[group]

class RegexFormat(BaseFormat):

    def __init__(self, name, regex, date_format=None):
        super(RegexFormat, self).__init__(name)
        if regex is not None:
            self.regex = re.compile(regex)
        if date_format is not None:
            self.date_format = date_format
        self.matched = None

    def check_format_line(self, line):
        return self.match(line)

    def match(self,line):
        if not self.regex:
            return None
        match_result = self.regex.match(line)
        if match_result:
            self.matched = match_result.groupdict()
        else:
            self.matched = None
        return match_result

    def get(self, key):
        try:
            return self.matched[key]
        except KeyError:
            raise BaseFormatException("Cannot find group '%s'." % key)

    def get_all(self,):
        return self.matched

    def remove_ignored_groups(self, groups):
        for group in groups:
            del self.matched[group]

class W3cExtendedFormat(RegexFormat):

    FIELDS_LINE_PREFIX = '#Fields: '

    fields = {
        'date': '(?P<date>\d+[-\d+]+',
        'time': '[\d+:]+)[.\d]*?', # TODO should not assume date & time will be together not sure how to fix ATM.
        'cs-uri-stem': '(?P<path>/\S*)',
        'cs-uri-query': '(?P<query_string>\S*)',
        'c-ip': '"?(?P<ip>[\w*.:-]*)"?',
        'cs(User-Agent)': '(?P<user_agent>".*?"|\S*)',
        'cs(Referer)': '(?P<referrer>\S+)',
        'sc-status': '(?P<status>\d+)',
        'sc-bytes': '(?P<length>\S+)',
        'cs-host': '(?P<host>\S+)',
        'cs-method': '(?P<method>\S+)',
        'cs-username': '(?P<userid>\S+)',
        'time-taken': '(?P<generation_time_secs>[.\d]+)'
    }

    def __init__(self):
        super(W3cExtendedFormat, self).__init__('w3c_extended', None, '%Y-%m-%d %H:%M:%S')

    def check_format(self, file):
        self.create_regex(file)

        # if we couldn't create a regex, this file does not follow the W3C extended log file format
        if not self.regex:
            try:
                file.seek(0)
            except IOError:
                pass

            return

        first_line = file.readline()

        try:
            file.seek(0)
        except IOError:
            pass

        return self.check_format_line(first_line)

    def create_regex(self, file):
        fields_line = None
        #if config.options.w3c_fields:
        #    fields_line = config.options.w3c_fields

        # collect all header lines up until the Fields: line
        # if we're reading from stdin, we can't seek, so don't read any more than the Fields line
        header_lines = []
        while fields_line is None:
            line = file.readline().strip()

            if not line:
                continue

            if not line.startswith('#'):
                break

            if line.startswith(W3cExtendedFormat.FIELDS_LINE_PREFIX):
                fields_line = line
            else:
                header_lines.append(line)

        if not fields_line:
            return

        # store the header lines for a later check for IIS
        self.header_lines = header_lines

        # Parse the 'Fields: ' line to create the regex to use
        full_regex = []

        expected_fields = type(self).fields.copy() # turn custom field mapping into field => regex mapping

        # if the --w3c-time-taken-millisecs option is used, make sure the time-taken field is interpreted as milliseconds
        #if config.options.w3c_time_taken_in_millisecs:
        #    expected_fields['time-taken'] = '(?P<generation_time_milli>[\d.]+)'

        for mapped_field_name, field_name in config.options.custom_w3c_fields.iteritems():
            expected_fields[mapped_field_name] = expected_fields[field_name]
            del expected_fields[field_name]

        # add custom field regexes supplied through --w3c-field-regex option
        #for field_name, field_regex in config.options.w3c_field_regexes.iteritems():
        #    expected_fields[field_name] = field_regex

        # Skip the 'Fields: ' prefix.
        fields_line = fields_line[9:].strip()
        for field in re.split('\s+', fields_line):
            try:
                regex = expected_fields[field]
            except KeyError:
                regex = '(?:".*?"|\S+)'
            full_regex.append(regex)
        full_regex = '\s+'.join(full_regex)

        logging.debug("Based on 'Fields:' line, computed regex to be %s", full_regex)

        self.regex = re.compile(full_regex)

    def check_for_iis_option(self):
       logging.info("WARNING: IIS log file being parsed without --w3c-time-taken-milli option. IIS"
                         " stores millisecond values in the time-taken field. If your logfile does this, the aforementioned"
                         " option must be used in order to get accurate generation times.")

    def _is_iis(self):
        return len([line for line in self.header_lines if 'internet information services' in line.lower() or 'iis' in line.lower()]) > 0

    def _is_time_taken_milli(self):
        return 'generation_time_milli' not in self.regex.pattern

class IisFormat(W3cExtendedFormat):

    fields = W3cExtendedFormat.fields.copy()
    fields.update({
        'time-taken': '(?P<generation_time_milli>[.\d]+)',
        'sc-win32-status': '(?P<__win32_status>\S+)' # this group is useless for log importing, but capturing it
                                                     # will ensure we always select IIS for the format instead of
                                                     # W3C logs when detecting the format. This way there will be
                                                     # less accidental importing of IIS logs w/o --w3c-time-taken-milli.
    })

    def __init__(self):
        super(IisFormat, self).__init__()

        self.name = 'iis'

class ShoutcastFormat(W3cExtendedFormat):

    fields = W3cExtendedFormat.fields.copy()
    fields.update({
        'c-status': '(?P<status>\d+)',
        'x-duration': '(?P<generation_time_secs>[.\d]+)'
    })

    def __init__(self):
        super(ShoutcastFormat, self).__init__()

        self.name = 'shoutcast'

    def get(self, key):
        if key == 'user_agent':
            user_agent = super(ShoutcastFormat, self).get(key)
            return urllib2.unquote(user_agent)
        else:
            return super(ShoutcastFormat, self).get(key)

class AmazonCloudFrontFormat(W3cExtendedFormat):

    fields = W3cExtendedFormat.fields.copy()
    fields.update({
        'x-event': '(?P<event_action>\S+)',
        'x-sname': '(?P<event_name>\S+)',
        'cs-uri-stem': '(?:rtmp:/)?(?P<path>/\S*)',
        'c-user-agent': '(?P<user_agent>".*?"|\S+)',

        # following are present to match cloudfront instead of W3C when we know it's cloudfront
        'x-edge-location': '(?P<x_edge_location>".*?"|\S+)',
        'x-edge-result-type': '(?P<x_edge_result_type>".*?"|\S+)',
        'x-edge-request-id': '(?P<x_edge_request_id>".*?"|\S+)',
        'x-host-header': '(?P<x_host_header>".*?"|\S+)'
    })

    def __init__(self):
        super(AmazonCloudFrontFormat, self).__init__()

        self.name = 'amazon_cloudfront'

    def get(self, key):
        if key == 'event_category' and 'event_category' not in self.matched:
            return 'cloudfront_rtmp'
        elif key == 'status' and 'status' not in self.matched:
            return '200'
        elif key == 'user_agent':
            user_agent = super(AmazonCloudFrontFormat, self).get(key)
            return urllib2.unquote(user_agent)
        else:
            return super(AmazonCloudFrontFormat, self).get(key)

_HOST_PREFIX = '(?P<host>[\w\-\.]*)(?::\d+)?\s+'

_COMMON_LOG_FORMAT = (
    '(?P<ip>[\w*.:-]+)\s+\S+\s+(?P<userid>\S+)\s+\[(?P<date>.*?)\s+(?P<timezone>.*?)\]\s+'
    '"(?P<method>\S+)\s+(?P<path>.*?)\s+\S+"\s+(?P<status>\d+)\s+(?P<length>\S+)'
)
_NCSA_EXTENDED_LOG_FORMAT = (_COMMON_LOG_FORMAT +
    '\s+"(?P<referrer>.*?)"\s+"(?P<user_agent>.*?)"'
)
_S3_LOG_FORMAT = (
    '\S+\s+(?P<host>\S+)\s+\[(?P<date>.*?)\s+(?P<timezone>.*?)\]\s+(?P<ip>[\w*.:-]+)\s+'
    '(?P<userid>\S+)\s+\S+\s+\S+\s+\S+\s+"(?P<method>\S+)\s+(?P<path>.*?)\s+\S+"\s+(?P<status>\d+)\s+\S+\s+(?P<length>\S+)\s+'
    '\S+\s+\S+\s+\S+\s+"(?P<referrer>.*?)"\s+"(?P<user_agent>.*?)"'
)
_ICECAST2_LOG_FORMAT = ( _NCSA_EXTENDED_LOG_FORMAT +
    '\s+(?P<session_time>[0-9-]+)'
)
_ELB_LOG_FORMAT = (
    '(?P<date>[0-9-]+T[0-9:]+)\.\S+\s+\S+\s+(?P<ip>[\w*.:-]+):\d+\s+\S+:\d+\s+\S+\s+(?P<generation_time_secs>\S+)\s+\S+\s+'
    '(?P<status>\d+)\s+\S+\s+\S+\s+(?P<length>\S+)\s+'
    '"\S+\s+\w+:\/\/(?P<host>[\w\-\.]*):\d+(?P<path>\/\S*)\s+[^"]+"\s+"(?P<user_agent>[^"]+)"\s+\S+\s+\S+'
)

_OVH_FORMAT = (
    '(?P<ip>\S+)\s+' + _HOST_PREFIX + '(?P<userid>\S+)\s+\[(?P<date>.*?)\s+(?P<timezone>.*?)\]\s+'
    '"\S+\s+(?P<path>.*?)\s+\S+"\s+(?P<status>\S+)\s+(?P<length>\S+)'
    '\s+"(?P<referrer>.*?)"\s+"(?P<user_agent>.*?)"'
)

FORMATS = {
    'common': RegexFormat('common', _COMMON_LOG_FORMAT),
    'common_vhost': RegexFormat('common_vhost', _HOST_PREFIX + _COMMON_LOG_FORMAT),
    'ncsa_extended': RegexFormat('ncsa_extended', _NCSA_EXTENDED_LOG_FORMAT),
    'common_complete': RegexFormat('common_complete', _HOST_PREFIX + _NCSA_EXTENDED_LOG_FORMAT),
    'w3c_extended': W3cExtendedFormat(),
    'amazon_cloudfront': AmazonCloudFrontFormat(),
    'iis': IisFormat(),
    'shoutcast': ShoutcastFormat(),
    's3': RegexFormat('s3', _S3_LOG_FORMAT),
    'icecast2': RegexFormat('icecast2', _ICECAST2_LOG_FORMAT),
    'elb': RegexFormat('elb', _ELB_LOG_FORMAT, '%Y-%m-%dT%H:%M:%S'),
    'nginx_json': JsonFormat('nginx_json'),
    'ovh': RegexFormat('ovh', _OVH_FORMAT)
}

##
## Code.
##

class Configuration(object):
    """
    Stores all the configuration options by reading sys.argv and parsing,
    if needed, the config.inc.php.

    It has 2 attributes: options and filenames.
    """

    class Error(Exception):
        pass

    def _create_parser(self):
        matomoConfig = None
        with open("matomo_config.yaml", 'r') as stream:
            try:
                matomoConfig=yaml.load(stream, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                print(exc)


        """
        Initialize and return the OptionParser instance.
        """
        self.options = matomoConfig
        return self.options


    def _parse_args(self, options):
        """
        Parse the command line args and create self.options and self.filenames.
        """
        filePath = os.path.abspath(os.path.abspath(sys.argv[-1]))
        self.filenames  = [(filePath+"/"+x) for x in os.listdir(filePath)]
        # Configure logging before calling logging.{debug,info}.
        logging.basicConfig(
            format='%(asctime)s: [%(levelname)s] %(message)s',
            level=logging.INFO,
        )

    def __init__(self):
        self._parse_args(self._create_parser())

    def get_resolver(self):
        if self.options.site_id:
            logging.debug('Resolver: static')
            return StaticResolver(self.options.site_id)
        else:
            logging.debug('Resolver: dynamic')
            return DynamicResolver()



class UrlHelper(object):

    @staticmethod
    def convert_array_args(args):
        """
        Converts PHP deep query param arrays (eg, w/ names like hsr_ev[abc][0][]=value) into a nested list/dict
        structure that will convert correctly to JSON.
        """

        final_args = {}
        for key, value in args.iteritems():
            indices = key.split('[')
            if '[' in key:
                # contains list of all indices, eg for abc[def][ghi][] = 123, indices would be ['abc', 'def', 'ghi', '']
                indices = [i.rstrip(']') for i in indices]

                # navigate the multidimensional array final_args, creating lists/dicts when needed, using indices
                element = final_args
                for i in range(0, len(indices) - 1):
                    idx = indices[i]

                    # if there's no next key, then this element is a list, otherwise a dict
                    element_type = list if not indices[i + 1] else dict
                    if idx not in element or not isinstance(element[idx], element_type):
                        element[idx] = element_type()

                    element = element[idx]

                # set the value in the final container we navigated to
                if not indices[-1]: # last indice is '[]'
                    element.append(value)
                else: # last indice has a key, eg, '[abc]'
                    element[indices[-1]] = value
            else:
                final_args[key] = value

        return UrlHelper._convert_dicts_to_arrays(final_args)

    @staticmethod
    def _convert_dicts_to_arrays(d):
        # convert dicts that have contiguous integer keys to arrays
        for key, value in d.iteritems():
            if not isinstance(value, dict):
                continue

            if UrlHelper._has_contiguous_int_keys(value):
                d[key] = UrlHelper._convert_dict_to_array(value)
            else:
                d[key] = UrlHelper._convert_dicts_to_arrays(value)

        return d

    @staticmethod
    def _has_contiguous_int_keys(d):
        for i in range(0, len(d)):
            if str(i) not in d:
                return False
        return True

    @staticmethod
    def _convert_dict_to_array(d):
        result = []
        for i in range(0, len(d)):
            result.append(d[str(i)])
        return result


class Matomo(object):
    """
    Make requests to Matomo.
    """
    class Error(Exception):

        def __init__(self, message, code = None):
            super(Exception, self).__init__(message)

            self.code = code

    class RedirectHandlerWithLogging(urllib2.HTTPRedirectHandler):
        """
        Special implementation of HTTPRedirectHandler that logs redirects in debug mode
        to help users debug system issues.
        """

        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            logging.debug("Request redirected (code: %s) to '%s'" % (code, newurl))

            return urllib2.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, hdrs, newurl)

    @staticmethod
    def _call(path, args, headers=None, url=None, data=None):
        """
        Make a request to the Matomo site. It is up to the caller to format
        arguments, to embed authentication, etc.
        """
        if url is None:
            url = config.options['Matomo_Parameters']['matomo_url']
        headers = headers or {}

        if data is None:
            # If Content-Type isn't defined, PHP do not parse the request's body.
            headers['Content-type'] = 'application/x-www-form-urlencoded'
            data = urllib.urlencode(args)
        elif not isinstance(data, basestring) and headers['Content-type'] == 'application/json':
            data = json.dumps(data)

            if args:
                path = path + '?' + urllib.urlencode(args)

        headers['User-Agent'] = 'Matomo/LogImport'

        try:
            timeout = config.options['Matomo_Parameters']['default_socket_timeout']
        except:
            timeout = None # the config global object may not be created at this point

        request = urllib2.Request(url + path, data, headers)


        # Use non-default SSL context if invalid certificates shall be
        # accepted.
        '''
        if config.options.accept_invalid_ssl_certificate and \
                sys.version_info >= (2, 7, 9):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            https_handler_args = {'context': ssl_context}
        else:
            https_handler_args = {}
        opener = urllib2.build_opener(
            Matomo.RedirectHandlerWithLogging(),
            urllib2.HTTPSHandler(**https_handler_args))
        response = opener.open(request, timeout = timeout)
        result = response.read()
        response.close()
        return result
        '''
        https_handler_args = {}
        opener = urllib2.build_opener(
            Matomo.RedirectHandlerWithLogging(),
            urllib2.HTTPSHandler(**https_handler_args))
        response = opener.open(request, timeout = timeout)
        result = response.read()
        response.close()
        return result

    @staticmethod
    def _call_api(method, **kwargs):
        """
        Make a request to the Matomo API taking care of authentication, body
        formatting, etc.
        """
        args = {
            'module' : 'API',
            'format' : 'json2',
            'method' : method,
            'filter_limit' : '-1',
        }
        if kwargs:
            args.update(kwargs)

        # Convert lists into appropriate format.
        # See: http://developer.matomo.org/api-reference/reporting-api#passing-an-array-of-data-as-a-parameter
        # Warning: we have to pass the parameters in order: foo[0], foo[1], foo[2]
        # and not foo[1], foo[0], foo[2] (it will break Matomo otherwise.)
        final_args = []
        for key, value in args.iteritems():
            if isinstance(value, (list, tuple)):
                for index, obj in enumerate(value):
                    final_args.append(('%s[%d]' % (key, index), obj))
            else:
                final_args.append((key, value))


#        logging.debug('%s' % final_args)
#        logging.debug('%s' % url)

        res = Matomo._call('/', final_args, url=url)

        try:
            return json.loads(res)
        except ValueError:
            raise urllib2.URLError('Matomo returned an invalid response: ' + res)

    @staticmethod
    def _call_wrapper(func, expected_response, on_failure, *args, **kwargs):
        """
        Try to make requests to Matomo at most MATOMO_FAILURE_MAX_RETRY times.
        """
        errors = 0
        while True:
            try:
                response = func(*args, **kwargs)
                if expected_response is not None and response != expected_response:
                    if on_failure is not None:
                        error_message = on_failure(response, kwargs.get('data'))
                    else:
                        error_message = "didn't receive the expected response. Response was %s " % response

                    raise urllib2.URLError(error_message)
                return response
            except (urllib2.URLError, httplib.HTTPException, ValueError, socket.timeout) as e:
                logging.info('Error when connecting to Matomo: %s', e)

                code = None
                if isinstance(e, urllib2.HTTPError):
                    # See Python issue 13211.
                    message = 'HTTP Error %s %s' % (e.code, e.msg)
                    code = e.code
                elif isinstance(e, urllib2.URLError):
                    message = e.reason
                else:
                    message = str(e)

                # decorate message w/ HTTP response, if it can be retrieved
                if hasattr(e, 'read'):
                    message = message + ", response: " + e.read()

                try:
                    delay_after_failure = config.options["Matomo_Parameters"]["delay_after_failure"]
                    max_attempts = config.options["Matomo_Parameters"]["default_max_attempts"]
                except NameError:
                    delay_after_failure = MATOMO_DEFAULT_DELAY_AFTER_FAILURE
                    max_attempts = MATOMO_DEFAULT_MAX_ATTEMPTS

                errors += 1
                if errors == max_attempts:
                    logging.info("Max number of attempts reached, server is unreachable!")

                    raise Matomo.Error(message, code)
                else:
                    logging.info("Retrying request, attempt number %d" % (errors + 1))

                    time.sleep(delay_after_failure)

    @classmethod
    def call(cls, path, args, expected_content=None, headers=None, data=None, on_failure=None):
        return cls._call_wrapper(cls._call, expected_content, on_failure, path, args, headers,
                                    data=data)

    @classmethod
    def call_api(cls, method, **kwargs):
        return cls._call_wrapper(cls._call_api, None, None, method, **kwargs)

class Recorder(object):
    """
    A Recorder fetches hits from the Queue and inserts them into Matomo using
    the API.
    """

    recorders = []

    def __init__(self):
        self.queue = Queue.Queue(maxsize=2)

        # if bulk tracking disabled, make sure we can store hits outside of the Queue
        #if not config.options.use_bulk_tracking:
        #    self.unrecorded_hits = []

    @classmethod
    def launch(cls, recorder_count):
        """
        Launch a bunch of Recorder objects in a separate thread.
        """
        for i in xrange(recorder_count):
            recorder = Recorder()
            cls.recorders.append(recorder)

            #run = recorder._run_bulk if config.options.use_bulk_tracking else recorder._run_single
            run = recorder._run_bulk
            t = threading.Thread(target=run)

            t.daemon = True
            t.start()
            logging.debug('Launched recorder')

    @classmethod
    def add_hits(cls, all_hits):
        """
        Add a set of hits to the recorders queue.
        """
        # Organize hits so that one client IP will always use the same queue.
        # We have to do this so visits from the same IP will be added in the right order.
        hits_by_client = [[] for r in cls.recorders]
        for hit in all_hits:
            hits_by_client[hit.get_visitor_id_hash() % len(cls.recorders)].append(hit)

        for i, recorder in enumerate(cls.recorders):
            recorder.queue.put(hits_by_client[i])

    @classmethod
    def wait_empty(cls):
        """
        Wait until all recorders have an empty queue.
        """
        for recorder in cls.recorders:
            recorder._wait_empty()

    def _run_bulk(self):
        while True:
            try:
                hits = self.queue.get()
            except:
                # TODO: we should log something here, however when this happens, logging.etc will throw
                return

            if len(hits) > 0:
                try:
                    self._record_hits(hits)
                except Matomo.Error as e:
                    fatal_error(e, hits[0].filename, hits[0].lineno) # approximate location of error
            self.queue.task_done()

    def _run_single(self):
        while True:

            if len(self.unrecorded_hits) > 0:
                hit = self.unrecorded_hits.pop(0)

                try:
                    self._record_hits([hit])
                except Matomo.Error as e:
                    fatal_error(e, hit.filename, hit.lineno)
            else:
                self.unrecorded_hits = self.queue.get()
                self.queue.task_done()

    def _wait_empty(self):
        """
        Wait until the queue is empty.
        """
        while True:
            if self.queue.empty():
                # We still have to wait for the last queue item being processed
                # (queue.empty() returns True before queue.task_done() is
                # called).
                self.queue.join()
                return
            time.sleep(1)

    def date_to_matomo(self, date):
        date, time = date.isoformat(sep=' ').split()
        return '%s %s' % (date, time.replace('-', ':'))

    def _get_hit_args(self, hit):
        """
        Returns the args used in tracking a hit, without the token_auth.
        """
        #site_id, main_url = resolver.resolve(hit)
        site_id = config.options['Matomo_Parameters']['idSite']
        #repositoy base url
        main_url = config.options['Matomo_Parameters']['repository_base_url']

        #stats.dates_recorded.add(hit.date.date())

        path = hit.path

        '''
        query_string_delimiter="?"
        if hit.query_string:
            path += config.options.query_string_delimiter + hit.query_string
        '''

        # only prepend main url / host if it's a path
        url_prefix = self._get_host_with_protocol(hit.host, main_url) if hasattr(hit, 'host') else main_url
        url = (url_prefix if path.startswith('/') else '') + path[:1024]

        # handle custom variables before generating args dict
        #if hit.is_robot:
        #    hit.add_visit_custom_var("Bot", hit.user_agent)
        #else:
        #    hit.add_visit_custom_var("Not-Bot", hit.user_agent)


        args = {
            'rec': '1',
            'apiv': '1',
            'url': url.encode('utf8'),
            'urlref': hit.referrer[:1024].encode('utf8'),
            'cip': hit.ip,
            'cdt': self.date_to_matomo(hit.date),
            'idsite': site_id,
            'ua': hit.user_agent.encode('utf8')
        }

        # idsite is already determined by resolver
        if 'idsite' in hit.args:
            del hit.args['idsite']
            
        args.update(hit.args)

        if hit.is_download:
            args['download'] = args['url']

        #if config.options.enable_bots:
        args['bots'] = '1'

        '''
        if hit.is_error or hit.is_redirect:
            args['action_name'] = '%s%sURL = %s%s' % (
                hit.status, '/',
                urllib.quote(args['url'], ''),
                ("%sFrom = %s" % (
                    '/',
                    urllib.quote(args['urlref'], '')
                ) if args['urlref'] != ''  else '')
            )
        '''
        if hit.generation_time_milli > 0:
            args['gt_ms'] = int(hit.generation_time_milli)

        if hit.event_category and hit.event_action:
            args['e_c'] = hit.event_category
            args['e_a'] = hit.event_action

            if hit.event_name:
                args['e_n'] = hit.event_name

        if hit.length:
            args['bw_bytes'] = hit.length

        # convert custom variable args to JSON
        if 'cvar' in args and not isinstance(args['cvar'], basestring):
            args['cvar'] = json.dumps(args['cvar'])

        if '_cvar' in args and not isinstance(args['_cvar'], basestring):
            args['_cvar'] = json.dumps(args['_cvar'])

        return UrlHelper.convert_array_args(args)

    def _get_host_with_protocol(self, host, main_url):
        if '://' not in host:
            parts = urlparse.urlparse(main_url)
            host = parts.scheme + '://' + host
        return host

    def _record_hits(self, hits):
        """
        Inserts several hits into Matomo.
        """

        #if not config.options.dry_run:
        data = {
            'token_auth': config.options['Matomo_Parameters']['token_auth'],
            'requests': [self._get_hit_args(hit) for hit in hits]
        }

        try:
            args = {}


            response = matomo.call(
                '/piwik.php', args=args,
                expected_content=None,
                headers={'Content-type': 'application/json'},
                data=data,
                on_failure=self._on_tracking_failure
            )
            # check for invalid requests
            try:
                response = json.loads(response)
            except:
                logging.info("bulk tracking returned invalid JSON")

                response = {}

            if ('invalid_indices' in response and isinstance(response['invalid_indices'], list) and
                response['invalid_indices']):
                invalid_count = len(response['invalid_indices'])

                invalid_lines = [str(hits[index].lineno) for index in response['invalid_indices']]
                invalid_lines_str = ", ".join(invalid_lines)

                #stats.invalid_lines.extend(invalid_lines)

                logging.info("The Matomo tracker identified %s invalid requests on lines: %s" % (invalid_count, invalid_lines_str))
            elif 'invalid' in response and response['invalid'] > 0:
                logging.info("The Matomo tracker identified %s invalid requests." % response['invalid'])
        except Matomo.Error as e:
            # if the server returned 400 code, BulkTracking may not be enabled
            if e.code == 400:
                fatal_error("Server returned status 400 (Bad Request).\nIs the BulkTracking plugin disabled?", hits[0].filename, hits[0].lineno)

            raise

        stats.count_lines_recorded.advance(len(hits))


    def _is_json(self, result):
        try:
            json.loads(result)
            return True
        except ValueError as e:
            return False

    def _on_tracking_failure(self, response, data):
        """
        Removes the successfully tracked hits from the request payload so
        they are not logged twice.
        """
        try:
            response = json.loads(response)
        except:
            # the response should be in JSON, but in case it can't be parsed just try another attempt
            logging.debug("cannot parse tracker response, should be valid JSON")
            return response

        # remove the successfully tracked hits from payload
        tracked = response['tracked']
        data['requests'] = data['requests'][tracked:]

        return response['message']

class Hit(object):
    """
    It's a simple container.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        super(Hit, self).__init__()


    def get_visitor_id_hash(self):
        visitor_id = self.ip
        '''
        if config.options.replay_tracking:
            for param_name_to_use in ['uid', 'cid', '_id', 'cip']:
                if param_name_to_use in self.args:
                    visitor_id = self.args[param_name_to_use]
                    break
        '''
        return abs(hash(visitor_id))

    def add_page_custom_var(self, key, value):
        """
        Adds a page custom variable to this Hit.
        """
        self._add_custom_var(key, value, 'cvar')

    def add_visit_custom_var(self, key, value):
        """
        Adds a visit custom variable to this Hit.
        """
        self._add_custom_var(key, value, '_cvar')

    def _add_custom_var(self, key, value, api_arg_name):
        if api_arg_name not in self.args:
            self.args[api_arg_name] = {}

        if isinstance(self.args[api_arg_name], basestring):
            logging.debug("Ignoring custom %s variable addition [ %s = %s ], custom var already set to string." % (api_arg_name, key, value))
            return

        index = len(self.args[api_arg_name]) + 1
        self.args[api_arg_name][index] = [key, value]

class CheckRobots(object):
    def _readCOUNTERRobots(self):
        with open('COUNTER_Robots_list.json') as json_file:
            self.counterRobotsList = json.load(json_file)
        return self.counterRobotsList

    def __init__(self):
        self._readCOUNTERRobots()


class Parser(object):
    """
    The Parser parses the lines in a specified file and inserts them into
    a Queue.
    """

    def __init__(self):
        self.check_methods = [method for name, method
                              in inspect.getmembers(self, predicate=inspect.ismethod)
                              if name.startswith('check_')]

    ## All check_* methods are called for each hit and must return True if the
    ## hit can be imported, False otherwise.


    def check_static(self, hit):
        if config.options["Matomo_Parameters"]["tracking_metadata"] is not None:
            for i in config.options["Matomo_Parameters"]["tracking_metadata"]:
                    pattern = re.compile(i)
                    if pattern.match(hit.path):
                        hit.add_page_custom_var("oaipmhID", config.options['Matomo_Parameters']['oaipmh_preamble']+":"+hit.path[len(i):])
                        hit.is_meta=True
                    break
        return True

    def check_download(self, hit):
        if config.options["Matomo_Parameters"]["tracking_download"] is not None:
            for i in config.options["Matomo_Parameters"]["tracking_download"]:
                pattern = re.compile(i)
                if pattern.match(hit.path):
                    hit.add_page_custom_var("oaipmhID", config.options['Matomo_Parameters']['oaipmh_preamble']+":"+hit.path[len(i):hit.path.rfind('/')])
                    hit.is_download = True
                break
        return True

    def check_user_agent(self, hit):
        user_agent = hit.user_agent
        for p in checkRobots.counterRobotsList:
            pattern = re.compile(p['pattern'])
            if pattern.search(user_agent):
                stats.count_lines_skipped_user_agent.increment()
                hit.is_robot = True
                break
        return True

    def check_http_error(self, hit):
        if hit.status[0] in ('4', '5'):
            hit.is_error = True
            return True
        return True

    def check_http_redirect(self, hit):
        if hit.status[0] == '3' and hit.status != '304':
             hit.is_redirect = True
             return True
        return True
    @staticmethod
    def check_format(lineOrFile):
        format = False
        format_groups = 0
        for name, candidate_format in FORMATS.iteritems():
            logging.debug("Check format %s", name)

            # skip auto detection for formats that can't be detected automatically
            if name == 'ovh':
                continue

            match = None
            try:
                if isinstance(lineOrFile, basestring):
                    match = candidate_format.check_format_line(lineOrFile)
                else:
                    match = candidate_format.check_format(lineOrFile)
            except Exception as e:
                logging.debug('Error in format checking: %s', traceback.format_exc())
                pass

            if match:
                logging.debug('Format %s matches', name)

                # compare format groups if this *BaseFormat has groups() method
                try:
                    # if there's more info in this match, use this format
                    match_groups = len(match.groups())

                    logging.debug('Format match contains %d groups' % match_groups)

                    if format_groups < match_groups:
                        format = candidate_format
                        format_groups = match_groups
                except AttributeError:
                    format = candidate_format

            else:
                logging.debug('Format %s does not match', name)

        # if the format is W3cExtendedFormat, check if the logs are from IIS and if so, issue a warning if the
        # --w3c-time-taken-milli option isn't set
        if isinstance(format, W3cExtendedFormat):
            format.check_for_iis_option()
        # dpie check
        # print "Format name "+format.name
        return format

    @staticmethod
    def detect_format(file):
        """
        Return the best matching format for this file, or None if none was found.
        """
        logging.debug('Detecting the log format')

        format = False

        # check the format using the file (for formats like the W3cExtendedFormat one)
        format = Parser.check_format(file)
        # check the format using the first N lines (to avoid irregular ones)
        lineno = 0
        limit = 100000
        while not format and lineno < limit:
            line = file.readline()
            if not line: # if at eof, don't keep looping
                break

            lineno = lineno + 1

            logging.debug("Detecting format against line %i" % lineno)
            format = Parser.check_format(line)

        try:
            file.seek(0)
        except IOError:
            pass

        if not format:
            fatal_error("cannot automatically determine the log format using the first %d lines of the log file. " % limit +
                        "\nMaybe try specifying the format with the --log-format-name command line argument." )
            return

        logging.debug('Format %s is the best match', format.name)
        return format

    def is_filtered(self, hit):
        host = None
        if hasattr(hit, 'host'):
            host = hit.host
        else:
            try:
                host = urlparse.urlparse(hit.path).hostname
            except:
                pass
        return (False, None)

    def parse(self, filename):
        """
        Parse the specified filename and insert hits in the queue.
        """
        def invalid_line(line, reason):
            logging.debug('Invalid line detected (%s): %s' % (reason, line))

        def filtered_line(line, reason):
            logging.debug('Filtered line out (%s): %s' % (reason, line))

        if filename == '-':
            filename = '(stdin)'
            file = sys.stdin
        else:
            if not os.path.exists(filename):
                print >> sys.stderr, "\n=====> Warning: File %s does not exist <=====" % filename
                return
            else:
                if filename.endswith('.bz2'):
                    open_func = bz2.BZ2File
                elif filename.endswith('.gz'):
                    open_func = gzip.open
                else:
                    open_func = open
                file = open_func(filename, 'r')


        format = self.detect_format(file)
        if format is None:
            return fatal_error(
                'Cannot guess the logs format. Please give one using '
                'either the --log-format-name or --log-format-regex option'
            )
        # Make sure the format is compatible with the resolver.
        #resolver.check_format(format)
        valid_lines_count = 0

        hits = []
        lineno = -1
        while True:
            line = file.readline()

            if not line: break
            lineno = lineno + 1

            stats.count_lines_parsed.increment()

            match = format.match(line)
            if not match:
                invalid_line(line, 'line did not match')
                continue

            valid_lines_count = valid_lines_count + 1

            hit = Hit(
                filename=filename,
                lineno=lineno,
                status=format.get('status'),
                full_path=format.get('path'),
                is_meta=False,
                is_download=False,
                is_robot=False,
                is_error=False,
                is_redirect=False,
                args={},
            )
            '''
            todelete
            # Add http method page cvar
            try:
                httpmethod = format.get('method')
                if config.options.track_http_method and httpmethod != '-':
                    hit.add_page_custom_var('HTTP-method', httpmethod)
            except:
                pass
            '''
            # W3cExtendedFormat detaults to - when there is no query string, but we want empty string
            hit.query_string = ''
            hit.path = hit.full_path

            try:
                hit.referrer = format.get('referrer')

                if hit.referrer.startswith('"'):
                    hit.referrer = hit.referrer[1:-1]
            except BaseFormatException:
                hit.referrer = ''
            if hit.referrer == '-':
                hit.referrer = ''

            try:
                hit.user_agent = format.get('user_agent')

                # in case a format parser included enclosing quotes, remove them so they are not
                # sent to Matomo
                if hit.user_agent.startswith('"'):
                    hit.user_agent = hit.user_agent[1:-1]
            except BaseFormatException:
                hit.user_agent = ''

            hit.ip = format.get('ip')

            #IP anonymization
            if config.options['Matomo_Parameters']['ip_anonymization'] is True:
                hit.ip = hit.ip.split('.')[0]+"."+hit.ip.split('.')[1]+".0.0"

            try:
                hit.length = int(format.get('length'))
            except (ValueError, BaseFormatException):
                # Some lines or formats don't have a length (e.g. 304 redirects, W3C logs)
                hit.length = 0

            try:
                hit.generation_time_milli = float(format.get('generation_time_milli'))
            except (ValueError, BaseFormatException):
                try:
                    hit.generation_time_milli = float(format.get('generation_time_micro')) / 1000
                except (ValueError, BaseFormatException):
                    try:
                        hit.generation_time_milli = float(format.get('generation_time_secs')) * 1000
                    except (ValueError, BaseFormatException):
                        hit.generation_time_milli = 0

            try:
                hit.host = format.get('host').lower().strip('.')
                if hit.host.startswith('"'):
                    hit.host = hit.host[1:-1]
            except BaseFormatException:
                # Some formats have no host.
                pass

            # Add userid
            try:
                hit.userid = None
                userid = format.get('userid')
                if userid != '-':
                    hit.args['uid'] = hit.userid = userid
            except:
                pass

            # add event info
            try:
                hit.event_category = hit.event_action = hit.event_name = None

                hit.event_category = format.get('event_category')
                hit.event_action = format.get('event_action')

                hit.event_name = format.get('event_name')
                if hit.event_name == '-':
                    hit.event_name = None
            except:
                pass

            # Check if the hit must be excluded.
            if not all((method(hit) for method in self.check_methods)):
                continue

            # Parse date.
            # We parse it after calling check_methods as it's quite CPU hungry, and
            # we want to avoid that cost for excluded hits.
            date_string = format.get('date')

            try:
                hit.date = datetime.datetime.strptime(date_string, format.date_format)
            except ValueError as e:
                invalid_line(line, 'invalid date or invalid format: %s' % str(e))
                continue

            # Parse timezone and substract its value from the date
            try:
                timezone = float(format.get('timezone'))
            except BaseFormatException:
                timezone = 0
            except ValueError:
                invalid_line(line, 'invalid timezone')
                continue

            if timezone:
                hit.date -= datetime.timedelta(hours=timezone/100)

            (is_filtered, reason) = self.is_filtered(hit)
            if is_filtered:
                filtered_line(line, reason)
                continue
            if (not hit.is_robot) and (hit.is_meta or hit.is_download):
                hits.append(hit)
            if (not hit.is_robot and hit.is_meta):
                stats.count_lines_static.increment()
            if (not hit.is_robot and hit.is_download):
                stats.count_lines_downloads.increment()

            #else:
             #print "not pass "+ hit.path + " "+ str(hit.is_meta)
            if len(hits) >= 200 * len(Recorder.recorders):
                Recorder.add_hits(hits)
                hits = []
        # add last chunk of hits
        if len(hits) > 0:
            Recorder.add_hits(hits)


class Statistics(object):
    """
    Store statistics about parsed logs and recorded entries.
    Can optionally print statistics on standard output every second.
    """

    class Counter(object):
        """
        Simple integers cannot be used by multithreaded programs. See:
        http://stackoverflow.com/questions/6320107/are-python-ints-thread-safe
        """
        def __init__(self):
            # itertools.count's implementation in C does not release the GIL and
            # therefore is thread-safe.
            self.counter = itertools.count(1)
            self.value = 0

        def increment(self):
            self.value = self.counter.next()

        def advance(self, n):
            for i in range(n):
                self.increment()

        def __str__(self):
            return str(int(self.value))

    def __init__(self):
        self.time_start = None
        self.time_stop = None

        self.count_lines_parsed = self.Counter()
        self.count_lines_recorded = self.Counter()

        # requests that the Matomo tracker considered invalid (or failed to track)
        self.invalid_lines = []

        # Do not match the regexp.
        self.count_lines_invalid = self.Counter()
        # Were filtered out.
        self.count_lines_filtered = self.Counter()
        # Static files.
        self.count_lines_static = self.Counter()
        # Ignored user-agents.
        self.count_lines_skipped_user_agent = self.Counter()
        # Downloads
        self.count_lines_downloads = self.Counter()

        # Misc
        self.dates_recorded = set()
        self.monitor_stop = False

    def set_time_start(self):
        self.time_start = time.time()

    def set_time_stop(self):
        self.time_stop = time.time()

    def _compute_speed(self, value, start, end):
        delta_time = end - start
        if value == 0:
            return 0
        if delta_time == 0:
            return 'very high!'
        else:
            return value / delta_time

    def _round_value(self, value, base=100):
        return round(value * base) / base

    def _indent_text(self, lines, level=1):
        """
        Return an indented text. 'lines' can be a list of lines or a single
        line (as a string). One level of indentation is 4 spaces.
        """
        prefix = ' ' * (4 * level)
        if isinstance(lines, basestring):
            return prefix + lines
        else:
            return '\n'.join(
                prefix + line
                for line in lines
            )

    def print_summary(self):
        invalid_lines_summary = ''
        if self.invalid_lines:
            invalid_lines_summary = '''Invalid log lines
-----------------

The following lines were not tracked by Matomo, either due to a malformed tracker request or error in the tracker:

%s

''' % textwrap.fill(", ".join(self.invalid_lines), 80)

        print('''
%(invalid_lines)sLogs import summary
-------------------

    %(count_lines_recorded)d requests imported successfully
    %(count_lines_downloads)d requests were downloads
    %(count_lines_metadata)d requests were metadata
    %(count_lines_skipped_user_agent)d requests ignored done by bots, search engines...

Performance summary
-------------------

    Total time: %(total_time)d seconds
    Requests imported per second: %(speed_recording)s requests per second


''' % {

    'count_lines_recorded': self.count_lines_recorded.value,
    'count_lines_downloads': self.count_lines_downloads.value,
    'count_lines_metadata': self.count_lines_static.value,
    'count_lines_skipped_user_agent': self.count_lines_skipped_user_agent.value,
    'total_time': self.time_stop - self.time_start,
    'speed_recording': self._round_value(self._compute_speed(
            self.count_lines_recorded.value,
            self.time_start, self.time_stop,
        )),
    'invalid_lines': invalid_lines_summary
})

    ##
    ## The monitor is a thread that prints a short summary each second.
    ##

    def _monitor(self):
        latest_total_recorded = 0
        while not self.monitor_stop:
            current_total = stats.count_lines_recorded.value
            time_elapsed = time.time() - self.time_start

            print('%d lines parsed, %d lines recorded, %d records/sec (avg), %d records/sec (current)' % (
                stats.count_lines_parsed.value,
                current_total,
                current_total / time_elapsed if time_elapsed != 0 else 0,
                current_total - latest_total_recorded,
            ))
            latest_total_recorded = current_total
            time.sleep(1)

    def start_monitor(self):
        t = threading.Thread(target=self._monitor)
        t.daemon = True
        t.start()

    def stop_monitor(self):
        self.monitor_stop = True


def main():
    """
    Start the importing process.
    """
    stats.set_time_start()
    ''''
    if config.options.show_progress:
        stats.start_monitor()
    '''
    stats.start_monitor()
    #recorders = Recorder.launch(config.options.recorders)
    recorders = Recorder.launch(config.options["Matomo_Parameters"]["recorders"])

    try:
        for filename in config.filenames:
            parser.parse(filename)

        Recorder.wait_empty()
    except KeyboardInterrupt:
        pass

    stats.set_time_stop()
    '''
    if config.options.show_progress:
        stats.stop_monitor()
    '''
    stats.stop_monitor()
    stats.print_summary()

def fatal_error(error, filename=None, lineno=None):
    print >> sys.stderr, 'Fatal error: %s' % error
    if filename and lineno is not None:
        print >> sys.stderr, (
            'You can restart the import of "%s" from the point it failed by '
            'specifying --skip=%d on the command line.\n' % (filename, lineno)
        )
    os._exit(1)

if __name__ == '__main__':
    try:
        config = Configuration()
        checkRobots = CheckRobots()
        matomo = Matomo()
        stats = Statistics()
        parser = Parser()
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        pass