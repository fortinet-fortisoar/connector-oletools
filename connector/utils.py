import requests
import json
import datetime
import os,sys
from abc import abstractmethod
from connectors.core.connector import get_logger, ConnectorError
from .constants import LOGGER_NAME
IS_PY3 = sys.version_info[0] == 3

STRING_TYPES = (str, bytes)  # type: ignore
STRING_OBJ_TYPES = (str,)




logger = get_logger(LOGGER_NAME)


def invoke_rest_endpoint(config, endpoint, method='GET', data=None, headers=None):
    if headers is None:
        headers = {'accept': 'application/json'}

    # utility function for a sample rest based integration using basic authentication
    # change as required for the specific integration being built

    server_address = config.get('server_address')
    port = config.get('port', '443')
    username = config.get('username')
    password = config.get('password')
    protocol = config.get('protocol', 'https')
    verify_ssl = config.get('verify_ssl', True)
    if not server_address or not username or not password:
        raise ConnectorError('Missing required parameters')
    url = '{protocol}://{server_address}:{port}{endpoint}'.format(protocol=protocol.lower(),
                                                                  server_address=server_address,
                                                                  port=port,
                                                                  endpoint=endpoint)
    try:
        response = requests.request(method, url, auth=(username, password), verify=verify_ssl,
                                    data=json.dumps(data), headers=headers)
    except Exception as e:
        logger.exception('Error invoking endpoint: {0}'.format(endpoint))
        raise ConnectorError('Error: {0}'.format(str(e)))
    if response.ok:
        return response.json()
    else:
        logger.error(response.content)
        raise ConnectorError(response.content)


STRING_TYPES = (str, bytes)  # type: ignore

def create_clickable_url(url, text=None):
    """
    Make the given url clickable when in markdown format by concatenating itself, with the proper brackets

    :type url: ``Union[List[str], str]``
    :param url: the url of interest or a list of urls

    :type text: ``Union[List[str], str, None]``
    :param text: the text of the url or a list of texts of urls.

    :return: Markdown format for clickable url
    :rtype: ``Union[List[str], str]``

    """
    if not url:
        return None
    elif isinstance(url, list):
        if isinstance(text, list):
            assert len(url) == len(text), 'The URL list and the text list must be the same length.'
            return ['[{}]({})'.format(text, item) for text, item in zip(text, url)]
        return ['[{}]({})'.format(item, item) for item in url]
    return '[{}]({})'.format(text or url, url)

def url_to_clickable_markdown(data, url_keys):
    """
    Turn the given urls fields in to clickable url, used for the markdown table.

    :type data: ``[Union[str, List[Any], Dict[str, Any]]]``
    :param data: a dictionary or a list containing data with some values that are urls

    :type url_keys: ``List[str]``
    :param url_keys: the keys of the url's wished to turn clickable

    :return: markdown format for clickable url
    :rtype: ``[Union[str, List[Any], Dict[str, Any]]]``
    """

    if isinstance(data, list):
        data = [url_to_clickable_markdown(item, url_keys) for item in data]

    elif isinstance(data, dict):
        data = {key: create_clickable_url(value) if key in url_keys else url_to_clickable_markdown(data[key], url_keys)
                for key, value in data.items()}

    return data
def argToList(arg, separator=',', transform=None):
    """
        Converts a string representation of args to a python list

        :type arg: ``str`` or ``list``
        :param arg: Args to be converted (required)

        :type separator: ``str``
        :param separator: A string separator to separate the strings, the default is a comma.

        :type transform: ``callable``
        :param transform: A function transformer to transfer the returned list arguments.

        :return: A python list of args
        :rtype: ``list``
    """
    if not arg:
        return []

    result = []
    if isinstance(arg, list):
        result = arg
    elif isinstance(arg, STRING_TYPES):
        is_comma_separated = True
        if arg[0] == '[' and arg[-1] == ']':
            try:
                result = json.loads(arg)
                is_comma_separated = False
            except Exception:
                logger.debug('Failed to load {} as JSON, trying to split'.format(arg))  # type: ignore[str-bytes-safe]
        if is_comma_separated:
            result = [s.strip() for s in arg.split(separator)]
    else:
        result = [arg]

    if transform:
        return [transform(s) for s in result]

    return result

MARKDOWN_CHARS = r"\`*_{}[]()#+-!|"
def stringEscapeMD(st, minimal_escaping=False, escape_multiline=False):
    """
        Escape any chars that might break a markdown string

        :type st: ``str``
        :param st: The string to be modified (required)

        :type minimal_escaping: ``bool``
        :param minimal_escaping: Whether replace all special characters or table format only (optional)

        :type escape_multiline: ``bool``
        :param escape_multiline: Whether convert line-ending characters (optional)

        :return: A modified string
        :rtype: ``str``
    """
    if escape_multiline:
        st = st.replace('\r\n', '<br>')  # Windows
        st = st.replace('\r', '<br>')  # old Mac
        st = st.replace('\n', '<br>')  # Unix

    if minimal_escaping:
        for c in ('|', '`'):
            st = st.replace(c, '\\' + c)
    else:
        st = "".join(["\\" + str(c) if c in MARKDOWN_CHARS else str(c) for c in st])

    return st

def formatCell(data, is_pretty=True, json_transform=None):
    """
        Convert a given object to md while decending multiple levels


        :type data: ``str`` or ``list`` or ``dict``
        :param data: The cell content (required)

        :type is_pretty: ``bool``
        :param is_pretty: Should cell content be prettified (default is True)

        :type json_transform: ``JsonTransformer``
        :param json_transform: The Json transform object to transform the data

        :return: The formatted cell content as a string
        :rtype: ``str``
    """
    if json_transform is None:
        json_transform = JsonTransformer(flatten=True)

    return json_transform.json_to_str(data, is_pretty)

def flattenCell(data, is_pretty=True):
    """
        Flattens a markdown table cell content into a single string

        :type data: ``str`` or ``list``
        :param data: The cell content (required)

        :type is_pretty: ``bool``
        :param is_pretty: Should cell content be pretified (default is True)

        :return: A sting representation of the cell content
        :rtype: ``str``
    """
    indent = 4 if is_pretty else None
    if isinstance(data, STRING_TYPES):
        return data
    elif isinstance(data, list):
        string_list = []
        for d in data:
            try:
                string_list.append(d.decode('utf-8'))
            except UnicodeEncodeError:
                string_list.append(d.encode('utf-8'))

        return ',\n'.join(string_list)
    else:
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
class EntryFormat(object):
    """
    Enum: contains all the entry formats (e.g. HTML, TABLE, JSON, etc.)
    """
    HTML = 'html'
    TABLE = 'table'
    JSON = 'json'
    TEXT = 'text'
    DBOT_RESPONSE = 'dbotCommandResponse'
    MARKDOWN = 'markdown'

    @classmethod
    def is_valid_type(cls, _type):
        # type: (str) -> bool
        return _type in (
            EntryFormat.HTML,
            EntryFormat.TABLE,
            EntryFormat.JSON,
            EntryFormat.TEXT,
            EntryFormat.MARKDOWN,
            EntryFormat.DBOT_RESPONSE
        )
class EntryType(object):
    """
    Enum: contains all the entry types (e.g. NOTE, ERROR, WARNING, FILE, etc.)
    :return: None
    :rtype: ``None``
    """
    NOTE = 1
    DOWNLOAD_AGENT = 2
    FILE = 3
    ERROR = 4
    PINNED = 5
    USER_MANAGEMENT = 6
    IMAGE = 7
    PLAYGROUND_ERROR = 8
    ENTRY_INFO_FILE = 9
    VIDEO_FILE = 10
    WARNING = 11
    STATIC_VIDEO_FILE = 12
    MAP_ENTRY_TYPE = 15
    WIDGET = 17
    EXECUTION_METRICS = 19


class CommandResults:
    """
    CommandResults class - use to return results to warroom

    :type outputs_prefix: ``str``
    :param outputs_prefix: should be identical to the prefix in the yml contextPath in yml file. for example:
            CortexXDR.Incident

    :type outputs_key_field: ``str`` or ``list[str]``
    :param outputs_key_field: primary key field in the main object. If the command returns Incidents, and of the
            properties of Incident is incident_id, then outputs_key_field='incident_id'. If object has multiple
            unique keys, then list of strings is supported outputs_key_field=['id1', 'id2']

    :type outputs: ``list`` or ``dict``
    :param outputs: the data to be returned and will be set to context

    :type indicators: ``list``
    :param indicators: DEPRECATED: use 'indicator' instead.

    :type indicator: ``Common.Indicator``
    :param indicator: single indicator like Common.IP, Common.URL, Common.File, etc.

    :type readable_output: ``str``
    :param readable_output: (Optional) markdown string that will be presented in the warroom, should be human readable -
        (HumanReadable) - if not set, readable output will be generated

    :type raw_response: ``dict`` | ``list``
    :param raw_response: must be dictionary, if not provided then will be equal to outputs. usually must be the original
        raw response from the 3rd party service (originally Contents)

    :type indicators_timeline: ``IndicatorsTimeline``
    :param indicators_timeline: must be an IndicatorsTimeline. used by the server to populate an indicator's timeline.

    :type ignore_auto_extract: ``bool``
    :param ignore_auto_extract: must be a boolean, default value is False. Used to prevent AutoExtract on output.

    :type relationships: ``list of EntityRelationship``
    :param relationships: List of relationships of the indicator.

    :type mark_as_note: ``bool``
    :param mark_as_note: must be a boolean, default value is False. Used to mark entry as note.

    :type tags: ``list``
    :param tags:  must be a list, default value is None. Used to tag war room entries.

    :type entry_type: ``int`` code of EntryType
    :param entry_type: type of return value, see EntryType

    :type scheduled_command: ``ScheduledCommand``
    :param scheduled_command: manages the way the command should be polled.

    :type execution_metrics: ``ExecutionMetrics``
    :param execution_metrics: contains metric data about a command's execution

    :type replace_existing: ``bool``
    :param replace_existing: Replace the context value at outputs_prefix if it exists.
            Works only if outputs_prefix is a path to a nested value i.e., contains a period.
            For example, the "next token" result should always be overwritten. This response can be returned as follows:
            >>> CommandResults(
            >>>     readable_output=f'Next Token: {next_token}',
            >>>     outputs=next_token,
            >>>     outputs_prefix='Path.To.NextToken',
            >>>     replace_existing=True,
            >>> )

    :return: None
    :rtype: ``None``
    """

    def __init__(self, outputs_prefix=None,
                outputs_key_field=None,
                outputs=None,
                indicators=None,
                readable_output=None,
                raw_response=None,
                indicators_timeline=None,
                indicator=None,
                ignore_auto_extract=False,
                mark_as_note=False,
                tags=None,
                scheduled_command=None,
                relationships=None,
                entry_type=None,
                content_format=None,
                execution_metrics=None,
                replace_existing=False):
        # type: (str, object, object, list, str, object, IndicatorsTimeline, Common.Indicator, bool, bool, List[str], ScheduledCommand, list, int, str, List[Any], bool) -> None  # noqa: E501
        if raw_response is None:
            raw_response = outputs
        if outputs is not None:
            if not isinstance(outputs, dict) and not outputs_prefix:
                raise ConnectorError('outputs_prefix is missing')
            if outputs_prefix == '.':
                raise ConnectorError('outputs_prefix cannot be a period.')
        if indicators and indicator:
            raise ConnectorError('indicators is DEPRECATED, use only indicator')
        if entry_type is None:
            entry_type = EntryType.NOTE

        self.indicators = indicators  # type: Optional[List[Common.Indicator]]
        self.indicator = indicator  # type: Optional[Common.Indicator]
        self.entry_type = entry_type  # type: int

        self.outputs_prefix = outputs_prefix

        # this is public field, it is used by a lot of unit tests, so I don't change it
        self.outputs_key_field = outputs_key_field

        self._outputs_key_field = None  # type: Optional[List[str]]
        if not outputs_key_field:
            self._outputs_key_field = None
        elif isinstance(outputs_key_field, STRING_TYPES):
            self._outputs_key_field = [outputs_key_field]  # type: ignore[list-item]
        elif isinstance(outputs_key_field, list):
            self._outputs_key_field = outputs_key_field
        else:
            raise ConnectorError('outputs_key_field must be of type str or list')

        self.outputs = outputs
        self.raw_response = raw_response
        self.readable_output = readable_output
        self.indicators_timeline = indicators_timeline
        self.ignore_auto_extract = ignore_auto_extract
        self.mark_as_note = mark_as_note
        self.tags = tags
        self.scheduled_command = scheduled_command
        self.relationships = relationships
        self.execution_metrics = execution_metrics
        self.replace_existing = replace_existing

        if content_format is not None and not EntryFormat.is_valid_type(content_format):
            raise ConnectorError('content_format {} is invalid, see CommonServerPython.EntryFormat'.format(content_format))
        self.content_format = content_format

    def to_context(self):
        outputs = {}  # type: dict
        relationships = []  # type: list
        tags = []  # type: list
        if self.readable_output:
            human_readable = self.readable_output
        else:
            human_readable = None  # type: ignore[assignment]
        raw_response = self.raw_response  # type: ignore[assignment]
        indicators_timeline = []  # type: ignore[assignment]
        ignore_auto_extract = False  # type: bool
        mark_as_note = False  # type: bool
        exec_metrics = None  # type: ignore[assignment]

        indicators = [self.indicator] if self.indicator else self.indicators

        if indicators:
            for indicator in indicators:
                context_outputs = indicator.to_context()

                for key, value in context_outputs.items():
                    if key not in outputs:
                        outputs[key] = []

                    outputs[key].append(value)

        if self.tags:
            tags = self.tags  # type: ignore[assignment]

        if self.ignore_auto_extract:
            ignore_auto_extract = True

        if self.mark_as_note:
            mark_as_note = True

        if self.indicators_timeline:
            indicators_timeline = self.indicators_timeline.indicators_timeline

        if self.outputs is not None and self.outputs != []:
            if not self.readable_output:
                # if markdown is not provided then create table by default
                if isinstance(self.outputs, (dict, list)):
                    human_readable = tableToMarkdown('Results', self.outputs)
                else:
                    human_readable = self.outputs  # type: ignore[assignment]
            if self.outputs_prefix and self.replace_existing:
                next_token_path, _, next_token_key = self.outputs_prefix.rpartition('.')
                if not next_token_path:
                    raise ConnectorError('outputs_prefix must be a nested path to replace an existing key.')
                outputs[next_token_path + '(true)'] = {next_token_key: self.outputs}
            elif self.outputs_prefix and self._outputs_key_field:
                # if both prefix and key field provided then create DT key
                formatted_outputs_key = ' && '.join(['val.{0} && val.{0} == obj.{0}'.format(key_field)
                                                    for key_field in self._outputs_key_field])
                outputs_key = '{0}({1})'.format(self.outputs_prefix, formatted_outputs_key)
                outputs[outputs_key] = self.outputs
            elif self.outputs_prefix:
                outputs[str(self.outputs_prefix)] = self.outputs
            else:
                outputs.update(self.outputs)  # type: ignore[call-overload]

        if self.relationships:
            relationships = [relationship.to_entry() for relationship in self.relationships if relationship.to_entry()]

        # using a local variable to avoid changing the object's attribute, see discussion on PR #18544.
        content_format = self.content_format
        if content_format is None:
            if isinstance(raw_response, STRING_TYPES + (int,)):
                content_format = EntryFormat.TEXT
            else:
                content_format = EntryFormat.JSON

        if self.execution_metrics:
            exec_metrics = self.execution_metrics
            self.entry_type = EntryType.EXECUTION_METRICS
            raw_response = 'Metrics reported successfully.'
            content_format = EntryFormat.TEXT
        return_entry = {
            'Type': self.entry_type,
            'ContentsFormat': content_format,
            'Contents': raw_response,
            'HumanReadable': human_readable,
            'EntryContext': outputs,
            'IndicatorTimeline': indicators_timeline,
            'IgnoreAutoExtract': bool(ignore_auto_extract),
            'Note': mark_as_note,
            'Relationships': relationships
        }
        if tags:
            # This is for backward compatibility reasons
            return_entry['Tags'] = tags
        if self.scheduled_command:
            return_entry.update(self.scheduled_command.to_results())

        if exec_metrics:
            return_entry.update({'APIExecutionMetrics': exec_metrics})

        return return_entry

class JsonTransformer:
    """
    A class to transform a json to

    :type flatten: ``bool``
    :param flatten: Should we flatten the json using `flattenCell` (for BC)

    :type keys: ``Set[str]``
    :param keys: Set of keys to keep

    :type is_nested: ``bool``
    :param is_nested: If look for nested

    :type func: ``Callable``
    :param func: A function to parse the json

    :return: None
    :rtype: ``None``
    """

    def __init__(self, flatten=False, keys=None, is_nested=False, func=None):
        """
        Constructor for JsonTransformer

        :type flatten: ``bool``
        :param flatten:  Should we flatten the json using `flattenCell` (for BC)

        :type keys: ``Iterable[str]``
        :param keys: an iterable of relevant keys list from the json. Notice we save it as a set in the class

        :type is_nested: ``bool``
        :param is_nested: Whether to search in nested keys or not

        :type func: ``Callable``
        :param func: A function to parse the json
        """
        if keys is None:
            keys = []
        self.keys = set(keys)
        self.is_nested = is_nested
        self.func = func
        self.flatten = flatten

    def json_to_str(self, json_input, is_pretty=True):
        if self.func:
            return self.func(json_input)
        if isinstance(json_input, STRING_TYPES):
            return json_input
        if self.flatten:
            if not isinstance(json_input, dict):
                return flattenCell(json_input, is_pretty)
            return '\n'.join(
                [u'{key}: {val}'.format(key=k, val=flattenCell(v, is_pretty)) for k, v in json_input.items()])  # for BC

        str_lst = []
        prev_path = []  # type: ignore
        for path, key, val in self.json_to_path_generator(json_input):
            str_path = ''
            full_tabs = '\t' * len(path)
            if path != prev_path:  # need to construct tha `path` string only of it changed from the last one
                common_prefix_index = len(os.path.commonprefix((prev_path, path)))  # type: ignore
                path_suffix = path[common_prefix_index:]

                str_path_lst = []
                for i, p in enumerate(path_suffix):
                    is_list = isinstance(p, int)
                    tabs = (common_prefix_index + i) * '\t'
                    path_value = p if not is_list else '-'
                    delim = ':\n' if not is_list else ''
                    str_path_lst.append('{tabs}**{path_value}**{delim}'.format(tabs=tabs, path_value=path_value, delim=delim))
                str_path = ''.join(str_path_lst)
                prev_path = path
                if path and isinstance(path[-1], int):
                    # if it is a beginning of a list, there is only one tab left
                    full_tabs = '\t'

            str_lst.append(
                '{path}{tabs}***{key}***: {val}'.format(path=str_path, tabs=full_tabs, key=key, val=flattenCell(val, is_pretty)))

        return '\n'.join(str_lst)

    def json_to_path_generator(self, json_input, path=None):
        """
        :type json_input: ``list`` or ``dict``
        :param json_input: The json input to transform
        :type path: ``List[str + int]``
        :param path: The path of the key, value pair inside the json

        :rtype ``Tuple[List[str + int], str, str]``
        :return:  A tuple. the second and third elements are key, values, and the first is their path in the json
        """
        if path is None:
            path = []
        is_in_path = not self.keys or any(p for p in path if p in self.keys)
        if isinstance(json_input, dict):
            for k, v in json_input.items():
                if is_in_path or k in self.keys:  # found data to return
                    # recurse until finding a primitive value
                    if not isinstance(v, dict) and not isinstance(v, list):
                        yield path, k, v
                    else:
                        for res in self.json_to_path_generator(v, path + [k]):  # this is yield from for python2 BC
                            yield res

                elif self.is_nested:
                    # recurse all the json_input to find the relevant data
                    for res in self.json_to_path_generator(v, path + [k]):  # this is yield from for python2 BC
                        yield res

        if isinstance(json_input, list):
            if not json_input or (not isinstance(json_input[0], list) and not isinstance(json_input[0], dict)):
                # if the items of the lists are primitive, put the values in one line
                yield path, 'values', ', '.join(json_input)
            else:
                for i, item in enumerate(json_input):
                    for res in self.json_to_path_generator(item, path + [i]):  # this is yield from for python2 BC
                        yield res

def tableToMarkdown(name, t, headers=None, headerTransform=None, removeNull=False, metadata=None, url_keys=None,
                      date_fields=None, json_transform_mapping=None, is_auto_json_transform=False, sort_headers=True):
    """
        Converts a demisto table in JSON form to a Markdown table

        :type name: ``str``
        :param name: The name of the table (required)

        :type t: ``dict`` or ``list``
        :param t: The JSON table - List of dictionaries with the same keys or a single dictionary (required)

        :type headers: ``list`` or ``string``
        :param headers: A list of headers to be presented in the output table (by order). If string will be passed
            then table will have single header. Default will include all available headers.

        :type headerTransform: ``function``
        :param headerTransform: A function that formats the original data headers (optional)

        :type removeNull: ``bool``
        :param removeNull: Remove empty columns from the table. Default is False

        :type metadata: ``str``
        :param metadata: Metadata about the table contents

        :type url_keys: ``list``
        :param url_keys: a list of keys in the given JSON table that should be turned in to clickable

        :type date_fields: ``list``
        :param date_fields: A list of date fields to format the value to human-readable output.

        :type json_transform_mapping: ``Dict[str, JsonTransformer]``
        :param json_transform_mapping: A mapping between a header key to corresponding JsonTransformer

        :type is_auto_json_transform: ``bool``
        :param is_auto_json_transform: Boolean to try to auto transform complex json

        :type sort_headers: ``bool``
        :param sort_headers: Sorts the table based on its headers only if the headers parameter is not specified

        :return: A string representation of the markdown table
        :rtype: ``str``
    """
    # Turning the urls in the table to clickable
    if url_keys:
        t = url_to_clickable_markdown(t, url_keys)

    mdResult = ''
    if name:
        mdResult = '### ' + name + '\n'

    if metadata:
        mdResult += metadata + '\n'

    if not t or len(t) == 0:
        mdResult += '**No entries.**\n'
        return mdResult

    if not headers and isinstance(t, dict) and len(t.keys()) == 1:
        # in case of a single key, create a column table where each element is in a different row.
        headers = list(t.keys())
        t = list(t.values())[0]

    if not isinstance(t, list):
        t = [t]

    if headers and isinstance(headers, STRING_TYPES):
        headers = [headers]

    if not isinstance(t[0], dict):
        # the table contains only simple objects (strings, numbers)
        # should be only one header
        if headers and len(headers) > 0:
            header = headers[0]
            t = [{header: item} for item in t]
        else:
            raise ConnectorError("Missing headers param for tableToMarkdown. Example: headers=['Some Header']")

    # in case of headers was not provided (backward compatibility)
    if not headers:
        headers = list(t[0].keys())
        if sort_headers or not IS_PY3:
            headers.sort()

    if removeNull:
        headers_aux = headers[:]
        for header in headers:
            if all(obj.get(header) in ('', None, [], {}) for obj in t):
                headers_aux.remove(header)
        headers = headers_aux

    if not json_transform_mapping:
        json_transform_mapping = {header: JsonTransformer(flatten=not is_auto_json_transform) for header in
                                headers}

    if t and len(headers) > 0:
        newHeaders = []
        if headerTransform is None:  # noqa
            def headerTransform(s): return stringEscapeMD(s, True, True)  # noqa
        for header in headers:
            newHeaders.append(headerTransform(header))
        mdResult += '|'
        if len(newHeaders) == 1:
            mdResult += newHeaders[0]
        else:
            mdResult += '|'.join(newHeaders)
        mdResult += '|\n'
        sep = '---'
        mdResult += '|' + '|'.join([sep] * len(headers)) + '|\n'
        for entry in t:
            entry_copy = entry.copy()
            if date_fields:
                for field in date_fields:
                    try:
                        entry_copy[field] = datetime.datetime.fromtimestamp(int(entry_copy[field]) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass

            vals = [stringEscapeMD((formatCell(entry_copy.get(h, ''), False,
                                                json_transform_mapping.get(h)) if entry_copy.get(h) is not None else ''),
                                    True, True) for h in headers]

            # this pipe is optional
            mdResult += '| '
            try:
                mdResult += ' | '.join(vals)
            except UnicodeDecodeError:
                vals = [str(v) for v in vals]
                mdResult += ' | '.join(vals)
            mdResult += ' |\n'

    else:
        mdResult += '**No entries.**\n'

    return mdResult

def argToBoolean(value):
    """
        Boolean-ish arguments that are passed through demisto.args() could be type bool or type string.
        This command removes the guesswork and returns a value of type bool, regardless of the input value's type.
        It will also return True for 'yes' and False for 'no'.

        :param value: the value to evaluate
        :type value: ``string|bool``

        :return: a boolean representatation of 'value'
        :rtype: ``bool``
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, STRING_OBJ_TYPES):
        if value.lower() in ['true', 'yes']:
            return True
        elif value.lower() in ['false', 'no']:
            return False
        else:
            raise ConnectorError('Argument does not contain a valid boolean-like value')
    else:
        raise ConnectorError('Argument is neither a string nor a boolean')   

def remove_nulls_from_dictionary(data):
    """
        Remove Null values from a dictionary. (updating the given dictionary)

        :type data: ``dict``
        :param data: The data to be added to the context (required)

        :return: No data returned
        :rtype: ``None``
    """
    list_of_keys = list(data.keys())[:]
    for key in list_of_keys:
        if data[key] in ('', None, [], {}, ()):
            del data[key]

class Common(object):
    class Indicator(object):
        """
        interface class
        """

        @abstractmethod
        def to_context(self):
            pass

        @staticmethod
        def create_context_table(data):
            """
            Gets a list of items of a specific class (such as CommunityNotes, Publications etc) and returns a context
            list.
            """
            table = []

            for item in data:
                table.append(item.to_context())

            return table

    class DBotScore(object):
        """
        DBotScore class

        :type indicator: ``str``
        :param indicator: indicator value, ip, hash, domain, url, etc

        :type indicator_type: ``DBotScoreType``
        :param indicator_type: use DBotScoreType class

        :type integration_name: ``str``
        :param integration_name: For integrations - The class will automatically determine the integration name.
                                For scripts - The class will use the given integration name.

        :type score: ``DBotScore``
        :param score: DBotScore.NONE, DBotScore.GOOD, DBotScore.SUSPICIOUS, DBotScore.BAD

        :type malicious_description: ``str``
        :param malicious_description: if the indicator is malicious and have explanation for it then set it to this field

        :type reliability: ``DBotScoreReliability``
        :param reliability: use DBotScoreReliability class

        :type message: ``str``
        :param message: Used to message on the api response, for example: When return api response is "Not found".

        :return: None
        :rtype: ``None``
        """
        NONE = 0
        GOOD = 1
        SUSPICIOUS = 2
        BAD = 3

        CONTEXT_PATH = 'DBotScore(val.Indicator && val.Indicator == obj.Indicator && val.Vendor == obj.Vendor ' \
                        '&& val.Type == obj.Type)'

        CONTEXT_PATH_PRIOR_V5_5 = 'DBotScore'

        def __init__(self, indicator, indicator_type, integration_name='', score=None, malicious_description=None,
                    reliability=None, message=None):

            if not DBotScoreType.is_valid_type(indicator_type):
                raise ConnectorError('indicator_type must be of type DBotScoreType enum')

            if not Common.DBotScore.is_valid_score(score):
                raise ConnectorError('indicator `score` must be of type DBotScore enum')

            if reliability and not DBotScoreReliability.is_valid_type(reliability):
                raise ConnectorError('reliability must be of type DBotScoreReliability enum')

            self.indicator = indicator
            self.indicator_type = indicator_type
            # For integrations - The class will automatically determine the integration name.
            self.integration_name = integration_name
            self.score = score
            self.malicious_description = malicious_description
            self.reliability = reliability
            self.message = message

        @staticmethod
        def is_valid_score(score):
            return score in (
                Common.DBotScore.NONE,
                Common.DBotScore.GOOD,
                Common.DBotScore.SUSPICIOUS,
                Common.DBotScore.BAD
            )

        @staticmethod
        def get_context_path():
            return Common.DBotScore.CONTEXT_PATH

        def to_context(self):
            dbot_context = {
                'Indicator': self.indicator,
                'Type': self.indicator_type,
                'Vendor': self.integration_name,
                'Score': self.score
            }

            if self.reliability:
                dbot_context['Reliability'] = self.reliability

            if self.message:
                dbot_context['Message'] = self.message

            ret_value = {
                Common.DBotScore.get_context_path(): dbot_context
            }
            return ret_value

        def to_readable(self):
            dbot_score_to_text = {0: 'Unknown',
                                1: 'Good',
                                2: 'Suspicious',
                                3: 'Bad'}
            return dbot_score_to_text.get(self.score, 'Undefined')

    class CustomIndicator(Indicator):

        def __init__(self, indicator_type, value, dbot_score, data, context_prefix, relationships=None):
            """
            :type indicator_type: ``Str``
            :param indicator_type: The name of the indicator type.

            :type value: ``Any``
            :param value: The value of the indicator.

            :type dbot_score: ``DBotScore``
            :param dbot_score: If custom indicator has a score then create and set a DBotScore object.

            :type data: ``Dict(Str,Any)``
            :param data: A dictionary containing all the param names and their values.

            :type context_prefix: ``Str``
            :param context_prefix: Will be used as the context path prefix.

            :type relationships: ``list of EntityRelationship``
            :param relationships: List of relationships of the indicator.

            :return: None
            :rtype: ``None``
            """
            if hasattr(DBotScoreType, indicator_type.upper()):
                raise ConnectorError('Creating a custom indicator type with an existing type name is not allowed')
            if not value:
                raise ConnectorError('value is mandatory for creating the indicator')
            if not context_prefix:
                raise ConnectorError('context_prefix is mandatory for creating the indicator')

            self.CONTEXT_PATH = '{context_prefix}(val.value && val.value == obj.value)'. \
                format(context_prefix=context_prefix)

            self.value = value
            self.relationships = relationships

            if not isinstance(dbot_score, Common.DBotScore):
                raise ConnectorError('dbot_score must be of type DBotScore')

            self.dbot_score = dbot_score
            self.indicator_type = indicator_type
            self.data = data
            INDICATOR_TYPE_TO_CONTEXT_KEY[indicator_type.lower()] = indicator_type.capitalize()

            for key in self.data:
                setattr(self, key, data[key])

        def to_context(self):
            custom_context = {
                'value': self.value
            }

            custom_context.update(self.data)

            ret_value = {
                self.CONTEXT_PATH: custom_context
            }  # type: Dict[str, Any]

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())
            ret_value[Common.DBotScore.get_context_path()]['Type'] = self.indicator_type

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                ret_value['Relationships'] = relationships_context

            return ret_value

    class IP(Indicator):
        """
        IP indicator class - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#ip

        :type ip: ``str``
        :param ip: IP address

        :type asn: ``str``
        :param asn: The autonomous system name for the IP address, for example: "AS8948".

        :type as_owner: ``str``
        :param as_owner: The autonomous system owner of the IP.

        :type region: ``str``
        :param region: The region in which the IP is located.

        :type port: ``str``
        :param port: Ports that are associated with the IP.

        :type internal: ``bool``
        :param internal: Whether or not the IP is internal or external.

        :type updated_date: ``date``
        :param updated_date: The date that the IP was last updated.

        :type registrar_abuse_name: ``str``
        :param registrar_abuse_name: The name of the contact for reporting abuse.

        :type registrar_abuse_address: ``str``
        :param registrar_abuse_address: The address of the contact for reporting abuse.

        :type registrar_abuse_country: ``str``
        :param registrar_abuse_country: The country of the contact for reporting abuse.

        :type registrar_abuse_network: ``str``
        :param registrar_abuse_network: The network of the contact for reporting abuse.

        :type registrar_abuse_phone: ``str``
        :param registrar_abuse_phone: The phone number of the contact for reporting abuse.

        :type registrar_abuse_email: ``str``
        :param registrar_abuse_email: The email address of the contact for reporting abuse.

        :type campaign: ``str``
        :param campaign: The campaign associated with the IP.

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol: The Traffic Light Protocol (TLP) color that is suitable for the IP.

        :type community_notes: ``CommunityNotes``
        :param community_notes: Notes on the IP that were given by the community.

        :type publications: ``Publications``
        :param publications: Publications on the ip that was published.

        :type threat_types: ``ThreatTypes``
        :param threat_types: Threat types that are associated with the file.

        :type hostname: ``str``
        :param hostname: The hostname that is mapped to this IP address.

        :type geo_latitude: ``str``
        :param geo_latitude: The geolocation where the IP address is located, in the format: latitude

        :type geo_longitude: ``str``
        :param geo_longitude: The geolocation where the IP address is located, in the format: longitude.

        :type geo_country: ``str``
        :param geo_country: The country in which the IP address is located.

        :type geo_description: ``str``
        :param geo_description: Additional information about the location.

        :type detection_engines: ``int``
        :param detection_engines: The total number of engines that checked the indicator.

        :type positive_engines: ``int``
        :param positive_engines: The number of engines that positively detected the indicator as malicious.

        :type organization_name: ``str``
        :param organization_name: The organization of the IP

        :type organization_type: ``str``
        :param organization_type:The organization type of the IP

        :type tags: ``str``
        :param tags: Tags of the IP.

        :type malware_family: ``str``
        :param malware_family: The malware family associated with the IP.

        :type feed_related_indicators: ``FeedRelatedIndicators``
        :param feed_related_indicators: List of indicators that are associated with the IP.

        :type relationships: ``list of EntityRelationship``
        :param relationships: List of relationships of the indicator.

        :type blocked: ``boolean``
        :param blocked: Is the indicator blocked.

        :type description: ``str``
        :param description: A general description of the indicator

        :type stix_id: ``str``
        :param stix_id: The STIX id representing the indicator

        :type whois_records: ``WhoisRecord``
        :param whois_records: List of whois records

        :type dbot_score: ``DBotScore``
        :param dbot_score: If IP has a score then create and set a DBotScore object.

        :type organization_prevalence: ``int``
        :param organization_prevalence: The number of times the indicator is detected in the organization.

        :type global_prevalence: ``int``
        :param global_prevalence: The number of times the indicator is detected across all organizations.

        :type organization_first_seen: ``str``
        :param organization_first_seen: ISO 8601 date time string; when the indicator was first seen in the organization.

        :type organization_last_seen: ``str``
        :param organization_last_seen: ISO 8601 date time string; the last time a specific organization encountered an indicator.

        :type first_seen_by_source: ``str``
        :param first_seen_by_source: ISO 8601 date time string; when the indicator was first seen by the source vendor.

        :type last_seen_by_source: ``str``
        :param last_seen_by_source: ISO 8601 date time string; when the indicator was last seen by the source vendor.

        :return: None
        :rtype: ``None``
        """

        CONTEXT_PATH = 'IP(val.Address && val.Address == obj.Address)'

        def __init__(self, ip, dbot_score, asn=None, as_owner=None, region=None, port=None, internal=None,
                    updated_date=None, registrar_abuse_name=None, registrar_abuse_address=None,
                    registrar_abuse_country=None, registrar_abuse_network=None, registrar_abuse_phone=None,
                    registrar_abuse_email=None, campaign=None, traffic_light_protocol=None,
                    community_notes=None, publications=None, threat_types=None,
                    hostname=None, geo_latitude=None, geo_longitude=None,
                    geo_country=None, geo_description=None, detection_engines=None, positive_engines=None,
                    organization_name=None, organization_type=None, feed_related_indicators=None, tags=None,
                    malware_family=None, relationships=None, blocked=None, description=None, stix_id=None,
                    whois_records=None, organization_prevalence=None,
                    global_prevalence=None, organization_first_seen=None, organization_last_seen=None,
                    first_seen_by_source=None, last_seen_by_source=None, ip_type="IP"):

            # Main value of the indicator
            self.ip = ip
            self.ip_type = ip_type

            # Core custom fields - IP
            self.blocked = blocked
            self.community_notes = community_notes
            self.description = description
            self.tags = tags
            self.geo_country = geo_country
            self.geo_latitude = geo_latitude
            self.geo_longitude = geo_longitude
            self.internal = internal
            self.stix_id = stix_id
            self.traffic_light_protocol = traffic_light_protocol
            self.whois_records = whois_records

            # Other custom fields
            self.asn = asn
            self.as_owner = as_owner
            self.region = region
            self.port = port
            self.updated_date = updated_date
            self.registrar_abuse_name = registrar_abuse_name
            self.registrar_abuse_address = registrar_abuse_address
            self.registrar_abuse_country = registrar_abuse_country
            self.registrar_abuse_network = registrar_abuse_network
            self.registrar_abuse_phone = registrar_abuse_phone
            self.registrar_abuse_email = registrar_abuse_email
            self.campaign = campaign
            self.publications = publications
            self.threat_types = threat_types
            self.hostname = hostname
            self.geo_description = geo_description
            self.detection_engines = detection_engines
            self.positive_engines = positive_engines
            self.organization_name = organization_name
            self.organization_type = organization_type
            self.feed_related_indicators = feed_related_indicators
            self.malware_family = malware_family
            self.relationships = relationships
            self.organization_prevalence = organization_prevalence
            self.global_prevalence = global_prevalence
            self.organization_first_seen = organization_first_seen
            self.organization_last_seen = organization_last_seen
            self.first_seen_by_source = first_seen_by_source
            self.last_seen_by_source = last_seen_by_source

            if not isinstance(dbot_score, Common.DBotScore):
                raise ConnectorError('dbot_score must be of type DBotScore')

            self.dbot_score = dbot_score

        def to_context(self):
            ip_context = {
                'Address': self.ip
            }

            if self.blocked:
                ip_context['Blocked'] = self.blocked

            if self.asn:
                ip_context['ASN'] = self.asn

            if self.as_owner:
                ip_context['ASOwner'] = self.as_owner

            if self.region:
                ip_context['Region'] = self.region

            if self.port:
                ip_context['Port'] = self.port

            if self.internal:
                ip_context['Internal'] = self.internal

            if self.stix_id:
                ip_context['STIXID'] = self.stix_id

            if self.updated_date:
                ip_context['UpdatedDate'] = self.updated_date

            if self.registrar_abuse_name or self.registrar_abuse_address or self.registrar_abuse_country or \
                    self.registrar_abuse_network or self.registrar_abuse_phone or self.registrar_abuse_email:
                ip_context['Registrar'] = {'Abuse': {}}
                if self.registrar_abuse_name:
                    ip_context['Registrar']['Abuse']['Name'] = self.registrar_abuse_name
                if self.registrar_abuse_address:
                    ip_context['Registrar']['Abuse']['Address'] = self.registrar_abuse_address
                if self.registrar_abuse_country:
                    ip_context['Registrar']['Abuse']['Country'] = self.registrar_abuse_country
                if self.registrar_abuse_network:
                    ip_context['Registrar']['Abuse']['Network'] = self.registrar_abuse_network
                if self.registrar_abuse_phone:
                    ip_context['Registrar']['Abuse']['Phone'] = self.registrar_abuse_phone
                if self.registrar_abuse_email:
                    ip_context['Registrar']['Abuse']['Email'] = self.registrar_abuse_email

            if self.campaign:
                ip_context['Campaign'] = self.campaign

            if self.description:
                ip_context['Description'] = self.description

            if self.traffic_light_protocol:
                ip_context['TrafficLightProtocol'] = self.traffic_light_protocol

            if self.community_notes:
                ip_context['CommunityNotes'] = self.create_context_table(self.community_notes)

            if self.publications:
                ip_context['Publications'] = self.create_context_table(self.publications)

            if self.threat_types:
                ip_context['ThreatTypes'] = self.create_context_table(self.threat_types)

            if self.whois_records:
                ip_context['WhoisRecords'] = self.create_context_table(self.whois_records)

            if self.hostname:
                ip_context['Hostname'] = self.hostname

            if self.geo_latitude or self.geo_country or self.geo_description:
                ip_context['Geo'] = {}

                if self.geo_latitude and self.geo_longitude:
                    ip_context['Geo']['Location'] = '{}:{}'.format(self.geo_latitude, self.geo_longitude)

                if self.geo_country:
                    ip_context['Geo']['Country'] = self.geo_country

                if self.geo_description:
                    ip_context['Geo']['Description'] = self.geo_description

            if self.organization_name or self.organization_type:
                ip_context['Organization'] = {}

                if self.organization_name:
                    ip_context['Organization']['Name'] = self.organization_name

                if self.organization_type:
                    ip_context['Organization']['Type'] = self.organization_type

            if self.detection_engines is not None:
                ip_context['DetectionEngines'] = self.detection_engines

            if self.positive_engines is not None:
                ip_context['PositiveDetections'] = self.positive_engines

            if self.feed_related_indicators:
                ip_context['FeedRelatedIndicators'] = self.create_context_table(self.feed_related_indicators)

            if self.tags:
                ip_context['Tags'] = self.tags

            if self.malware_family:
                ip_context['MalwareFamily'] = self.malware_family

            if self.organization_prevalence is not None:  # checking for `is not None` to allow `0`-value
                ip_context['OrganizationPrevalence'] = self.organization_prevalence

            if self.global_prevalence is not None:  # checking for `is not None` to allow `0`-value
                ip_context['GlobalPrevalence'] = self.global_prevalence

            if self.organization_first_seen:
                ip_context['OrganizationFirstSeen'] = self.organization_first_seen

            if self.organization_last_seen:
                ip_context['OrganizationLastSeen'] = self.organization_last_seen

            if self.first_seen_by_source:
                ip_context['FirstSeenBySource'] = self.first_seen_by_source

            if self.last_seen_by_source:
                ip_context['LastSeenBySource'] = self.last_seen_by_source

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                ip_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                ip_context['Relationships'] = relationships_context

            if self.ip_type == "IP":
                context_path = Common.IP.CONTEXT_PATH

            elif self.ip_type == "IPv6":
                context_path = Common.IP.CONTEXT_PATH.replace("IP", "IPv6")

            ret_value = {
                context_path: ip_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value

    class FileSignature(object):
        """
        FileSignature class
        :type authentihash: ``str``
        :param authentihash: The authentication hash.
        :type copyright: ``str``
        :param copyright: Copyright information.
        :type description: ``str``
        :param description: A description of the signature.
        :type file_version: ``str``
        :param file_version: The file version.
        :type internal_name: ``str``
        :param internal_name: The internal name of the file.
        :type original_name: ``str``
        :param original_name: The original name of the file.
        :return: None
        :rtype: ``None``
        """

        def __init__(self, authentihash, copyright, description, file_version, internal_name, original_name):
            self.authentihash = authentihash
            self.copyright = copyright
            self.description = description
            self.file_version = file_version
            self.internal_name = internal_name
            self.original_name = original_name

        def to_context(self):
            return {
                'Authentihash': self.authentihash,
                'Copyright': self.copyright,
                'Description': self.description,
                'FileVersion': self.file_version,
                'InternalName': self.internal_name,
                'OriginalName': self.original_name,
            }

    class FeedRelatedIndicators(object):
        """
        FeedRelatedIndicators class
        Implements Subject Indicators that are associated with Another indicator

        :type value: ``str``
        :param value: Indicators that are associated with the indicator.

        :type indicator_type: ``str``
        :param indicator_type: The type of the indicators that are associated with the indicator.

        :type description: ``str``
        :param description: The description of the indicators that are associated with the indicator.

        :return: None
        :rtype: ``None``
        """

        def __init__(self, value=None, indicator_type=None, description=None):
            self.value = value
            self.indicator_type = indicator_type
            self.description = description

        def to_context(self):
            return {
                'value': self.value,
                'type': self.indicator_type,
                'description': self.description
            }

    class Rank:
        """
        Single row in a rank grid field

        :type rank: float / int
        :param rank: A numerical rank value

        :type source: ``str``
        :param source: The name of the source from which the rank was taken
        """

        def __init__(self, rank=None, source=None):
            self.rank = rank
            self.source = source

        def to_context(self):
            return {
                'source': self.source,
                'rank': self.rank
            }

    class ExternalReference(object):
        """
        ExternalReference class
        Class to represent a single instance of an external reference for an indicator type.

        :type source_name: ``str``
        :param source_name: The name of the source referenced.

        :type source_id: ``str``
        :param source_id: The ID of the object in the external source.

        :return: None
        :rtype: ``None``
        """

        def __init__(self, source_name=None, source_id=None):
            self.source_name = source_name
            self.source_id = source_id

        def to_context(self):
            return {
                'sourcename': self.source_name,
                'sourceid': self.source_id,
            }

    class Certificates(object):
        """
        Certificates class
        Class to represent a single instance of a certificate for an indicator type.

        :type issued_to: ``str``
        :param issued_to: Who was the certificated issued to

        :type issued_by: ``str``
        :param issued_by: Who issued the certificate

        :type valid_from: ``str``
        :param valid_from: Since when is the certificate valid

        :type valid_to: ``str``
        :param valid_to: Till when is the certificate valid

        :return: None
        :rtype: ``None``
        """

        def __init__(self, issued_to=None, issued_by=None, valid_from=None, valid_to=None):
            self.issued_to = issued_to
            self.issued_by = issued_by
            self.valid_from = valid_from
            self.valid_to = valid_to

        def to_context(self):
            return {
                'issuedto': self.issued_to,
                'issuedby': self.issued_by,
                'validfrom': self.valid_from,
                'validto': self.valid_to
            }

    class Hash(object):
        """
        Hash class
        Class to represent a single instance of a hash for an indicator type.

        :type hash_type: ``str``
        :param hash_type: The type of the hash.

        :type hash_value: ``str``
        :param hash_value: The value of the hash.

        :return: None
        :rtype: ``None``
        """

        def __init__(self, hash_type=None, hash_value=None):
            self.hash_type = hash_type
            self.hash_value = hash_value

        def to_context(self):
            return {
                'type': self.hash_type,
                'value': self.hash_value,
            }

    class CommunityNotes(object):
        """
        CommunityNotes class
        Implements Subject Community Notes of a indicator

        :type note: ``str``
        :param note: Notes on the indicator that were given by the community.

        :type timestamp: ``Timestamp``
        :param timestamp: The time in which the note was published.

        :return: None
        :rtype: ``None``
        """

        def __init__(self, note=None, timestamp=None):
            self.note = note
            self.timestamp = timestamp

        def to_context(self):
            return {
                'note': self.note,
                'timestamp': self.timestamp,
            }

    class Publications(object):
        """
        Publications class
        Implements Subject Publications of a indicator

        :type source: ``str``
        :param source: The source in which the article was published.

        :type title: ``str``
        :param title: The name of the article.

        :type link: ``str``
        :param link: A link to the original article.

        :type timestamp: ``Timestamp``
        :param timestamp: The time in which the article was published.

        :return: None
        :rtype: ``None``
        """

        def __init__(self, source=None, title=None, link=None, timestamp=None):
            self.source = source
            self.title = title
            self.link = link
            self.timestamp = timestamp

        def to_context(self):
            return {
                'source': self.source,
                'title': self.title,
                'link': self.link,
                'timestamp': self.timestamp,
            }

    class Behaviors(object):
        """
        Behaviors class
        Implements Subject Behaviors of a indicator

        :type details: ``str``
        :param details:

        :type action: ``str``
        :param action:

        :return: None
        :rtype: ``None``
        """

        def __init__(self, details=None, action=None):
            self.details = details
            self.action = action

        def to_context(self):
            return {
                'details': self.details,
                'title': self.action,
            }

    class ThreatTypes(object):
        """
        ThreatTypes class
        Implements Subject ThreatTypes of a indicator

        :type threat_category: ``str``
        :param threat_category: The threat category associated to this indicator by the source vendor. For example,
        Phishing, Control, TOR, etc.

        :type threat_category_confidence: ``str``
        :param threat_category_confidence: Threat Category Confidence is the confidence level provided by the vendor
        for the threat type category
        For example a confidence of 90 for threat type category "malware" means that the vendor rates that this
        is 90% confidence of being a malware.

        :return: None
        :rtype: ``None``
        """

        def __init__(self, threat_category=None, threat_category_confidence=None):
            self.threat_category = threat_category
            self.threat_category_confidence = threat_category_confidence

        def to_context(self):
            return {
                'threatcategory': self.threat_category,
                'threatcategoryconfidence': self.threat_category_confidence,
            }

    class WhoisRecord(object):
        """
        WhoisRecord class
        Class to represent a single instance of a record for an indicator type.

        :type whois_record_type: ``str``
        :param whois_record_type: The type of the whois record.

        :type whois_record_value: ``str``
        :param whois_record_value: The value of the whois record.

        :type whois_record_date: ``Timestamp``
        :param whois_record_date: when was the whois record fetched

        :return: None
        :rtype: ``None``
        """

        def __init__(self, whois_record_type=None, whois_record_value=None, whois_record_date=None):
            self.whois_record_type = whois_record_type
            self.whois_record_value = whois_record_value
            self.whois_record_date = whois_record_date

        def to_context(self):
            return {
                'key': self.whois_record_type,
                'value': self.whois_record_value,
                'date': self.whois_record_date
            }

    class DNSRecord(object):
        """
        DNSRecord class
        Class to represent a single instance of a record for an indicator type.

        :type dns_record_type: ``str``
        :param dns_record_type: The type of the DNS record.

        :type dns_record_data: ``str``
        :param dns_record_data: The value of the whois record.

        :type dns_ttl: ``str``
        :param dns_ttl: The record TTL

        :return: None
        :rtype: ``None``
        """

        def __init__(self, dns_record_type=None, dns_ttl=None, dns_record_data=None):
            self.dns_record_type = dns_record_type
            self.dns_ttl = dns_ttl
            self.dns_record_data = dns_record_data

        def to_context(self):
            return {
                'type': self.dns_record_type,
                'ttl': self.dns_ttl,
                'data': self.dns_record_data
            }

    class CPE:
        """
        Represents one Common Platform Enumeration (CPE) object, see https://nvlpubs.nist.gov/nistpubs/legacy/ir/nistir7695.pdf

        :type cpe: ``str``
        :param cpe: a single CPE string

        :return: None
        :rtype: ``None``

        """

        def __init__(self, cpe=None):
            self.cpe = cpe

        def to_context(self):
            return {
                'CPE': self.cpe,
            }

    class File(Indicator):
        """
        File indicator class - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#file
        :type name: ``str``
        :param name: The full file name (including file extension).

        :type entry_id: ``str``
        :param entry_id: The ID for locating the file in the War Room.

        :type size: ``int``
        :param size: The size of the file in bytes.

        :type md5: ``str``
        :param md5: The MD5 hash of the file.

        :type sha1: ``str``
        :param sha1: The SHA1 hash of the file.

        :type sha256: ``str``
        :param sha256: The SHA256 hash of the file.

        :type sha512: ``str``
        :param sha512: The SHA512 hash of the file.

        :type ssdeep: ``str``
        :param ssdeep: The ssdeep hash of the file (same as displayed in file entries).

        :type extension: ``str``
        :param extension: The file extension, for example: "xls".

        :type file_type: ``str``
        :param file_type: The file type, as determined by libmagic (same as displayed in file entries).

        :type hostname: ``str``
        :param hostname: The name of the host where the file was found. Should match Path.

        :type path: ``str``
        :param path: The path where the file is located.

        :type company: ``str``
        :param company: The name of the company that released a binary.

        :type product_name: ``str``
        :param product_name: The name of the product to which this file belongs.

        :type digital_signature__publisher: ``str``
        :param digital_signature__publisher: The publisher of the digital signature for the file.

        :type signature: ``FileSignature``
        :param signature: File signature class

        :type actor: ``str``
        :param actor: The actor reference.

        :type tags: ``str``
        :param tags: Tags of the file.

        :type feed_related_indicators: ``FeedRelatedIndicators``
        :param feed_related_indicators: List of indicators that are associated with the file.

        :type malware_family: ``str``
        :param malware_family: The malware family associated with the File.

        :type campaign: ``str``
        :param campaign:

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol:

        :type community_notes: ``CommunityNotes``
        :param community_notes:  Notes on the file that were given by the community.

        :type publications: ``Publications``
        :param publications: Publications on the file that was published.

        :type threat_types: ``ThreatTypes``
        :param threat_types: Threat types that are associated with the file.

        :type imphash: ``str``
        :param imphash: The Imphash hash of the file.

        :type quarantined: ``bool``
        :param quarantined: Is the file quarantined or not.

        :type organization: ``str``
        :param organization: The organization of the file.

        :type associated_file_names: ``str``
        :param associated_file_names: File names that are known as associated to the file.

        :type behaviors: ``Behaviors``
        :param behaviors: list of behaviors associated with the file.

        :type relationships: ``list of EntityRelationship``
        :param relationships: List of relationships of the indicator.

        :type dbot_score: ``DBotScore``
        :param dbot_score: If file has a score then create and set a DBotScore object

        :type creation_date: ``str``
        :param creation_date: The date the file was created.

        :type description: ``str``
        :param description: File description.

        :type hashes: ``Hash``
        :param hashes: List of hashes associated with the file.

        :type stix_id: ``str``
        :param stix_id: File assigned STIX ID.

        :type organization_prevalence: ``int``
        :param organization_prevalence: The number of times the indicator is detected in the organization.

        :type global_prevalence: ``int``
        :param global_prevalence: The number of times the indicator is detected across all organizations.

        :type organization_first_seen: ``str``
        :param organization_first_seen: ISO 8601 date time string; when the indicator was first seen in the organization.

        :type organization_last_seen: ``str``
        :param organization_last_seen: ISO 8601 date time string; the last time a specific organization encountered an indicator.

        :type first_seen_by_source: ``str``
        :param first_seen_by_source: ISO 8601 date time string; when the indicator was first seen by the source vendor.

        :type last_seen_by_source: ``str``
        :param last_seen_by_source: ISO 8601 date time string; when the indicator was last seen by the source vendor.

        :rtype: ``None``
        :return: None
        """
        CONTEXT_PATH = 'File(val.MD5 && val.MD5 == obj.MD5 || val.SHA1 && val.SHA1 == obj.SHA1 || ' \
                        'val.SHA256 && val.SHA256 == obj.SHA256 || val.SHA512 && val.SHA512 == obj.SHA512 || ' \
                        'val.CRC32 && val.CRC32 == obj.CRC32 || val.CTPH && val.CTPH == obj.CTPH || ' \
                        'val.SSDeep && val.SSDeep == obj.SSDeep)'

        def __init__(self, dbot_score, name=None, entry_id=None, size=None, md5=None, sha1=None, sha256=None,
                    sha512=None, ssdeep=None, extension=None, file_type=None, hostname=None, path=None, company=None,
                    product_name=None, digital_signature__publisher=None, signature=None, actor=None, tags=None,
                    feed_related_indicators=None, malware_family=None, imphash=None, quarantined=None, campaign=None,
                    associated_file_names=None, traffic_light_protocol=None, organization=None, community_notes=None,
                    publications=None, threat_types=None, behaviors=None, relationships=None,
                    creation_date=None, description=None, hashes=None, stix_id=None, organization_prevalence=None,
                    global_prevalence=None, organization_first_seen=None, organization_last_seen=None,
                    first_seen_by_source=None, last_seen_by_source=None):

            # Main value of a file (Hashes)
            self.md5 = md5
            self.imphash = imphash
            self.sha1 = sha1
            self.sha256 = sha256
            self.sha512 = sha512
            self.ssdeep = ssdeep
            self.hashes = hashes

            # Core custom fields for File type
            self.associated_file_names = associated_file_names
            self.community_notes = community_notes
            self.creation_date = creation_date
            self.description = description
            self.extension = extension
            self.file_type = file_type
            self.path = path
            self.quarantined = quarantined
            self.size = size
            self.stix_id = stix_id
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol

            # Other custom fields
            self.name = name
            self.entry_id = entry_id
            self.hostname = hostname
            self.company = company
            self.product_name = product_name
            self.digital_signature__publisher = digital_signature__publisher
            self.signature = signature
            self.actor = actor
            self.organization = organization
            self.feed_related_indicators = feed_related_indicators
            self.malware_family = malware_family
            self.campaign = campaign
            self.publications = publications
            self.threat_types = threat_types
            self.behaviors = behaviors
            self.organization_prevalence = organization_prevalence
            self.global_prevalence = global_prevalence
            self.organization_first_seen = organization_first_seen
            self.organization_last_seen = organization_last_seen
            self.first_seen_by_source = first_seen_by_source
            self.last_seen_by_source = last_seen_by_source

            # XSOAR Fields
            self.relationships = relationships
            self.dbot_score = dbot_score

        def to_context(self):
            file_context = {'Hashes': []}  # type: dict

            if self.name:
                file_context['Name'] = self.name

            if self.hashes:
                file_context['Hashes'] = self.create_context_table(self.hashes)

            if self.entry_id:
                file_context['EntryID'] = self.entry_id

            if self.size:
                file_context['Size'] = self.size

            if self.md5:
                file_context['MD5'] = self.md5
                file_context['Hashes'].append({'type': 'MD5',
                                                'value': self.md5})

            if self.sha1:
                file_context['SHA1'] = self.sha1
                file_context['Hashes'].append({'type': 'SHA1',
                                                'value': self.sha1})

            if self.sha256:
                file_context['SHA256'] = self.sha256
                file_context['Hashes'].append({'type': 'SHA256',
                                                'value': self.sha256})

            if self.sha512:
                file_context['SHA512'] = self.sha512
                file_context['Hashes'].append({'type': 'SHA512',
                                                'value': self.sha512})

            if self.ssdeep:
                file_context['SSDeep'] = self.ssdeep
                file_context['Hashes'].append({'type': 'SSDeep',
                                                'value': self.ssdeep})

            if self.extension:
                file_context['Extension'] = self.extension

            if self.file_type:
                file_context['Type'] = self.file_type

            if self.hostname:
                file_context['Hostname'] = self.hostname

            if self.path:
                file_context['Path'] = self.path

            if self.company:
                file_context['Company'] = self.company

            if self.product_name:
                file_context['ProductName'] = self.product_name

            if self.digital_signature__publisher:
                file_context['DigitalSignature'] = {
                    'Published': self.digital_signature__publisher
                }

            if self.signature:
                file_context['Signature'] = self.signature.to_context()

            if self.actor:
                file_context['Actor'] = self.actor

            if self.tags:
                file_context['Tags'] = self.tags

            if self.feed_related_indicators:
                file_context['FeedRelatedIndicators'] = self.create_context_table(self.feed_related_indicators)

            if self.malware_family:
                file_context['MalwareFamily'] = self.malware_family

            if self.campaign:
                file_context['Campaign'] = self.campaign

            if self.traffic_light_protocol:
                file_context['TrafficLightProtocol'] = self.traffic_light_protocol

            if self.community_notes:
                file_context['CommunityNotes'] = self.create_context_table(self.community_notes)

            if self.publications:
                file_context['Publications'] = self.create_context_table(self.publications)

            if self.threat_types:
                file_context['ThreatTypes'] = self.create_context_table(self.threat_types)

            if self.imphash:
                file_context['Imphash'] = self.imphash
                file_context['Hashes'].append({'type': 'Imphash',
                                                'value': self.imphash})

            if self.quarantined:
                file_context['Quarantined'] = self.quarantined

            if self.organization:
                file_context['Organization'] = self.organization

            if self.associated_file_names:
                file_context['AssociatedFileNames'] = self.associated_file_names

            if self.behaviors:
                file_context['Behavior'] = self.create_context_table(self.behaviors)

            if self.organization_prevalence is not None:  # checking for `is not None` to allow `0`-value
                file_context['OrganizationPrevalence'] = self.organization_prevalence

            if self.global_prevalence is not None:  # checking for `is not None` to allow `0`-value
                file_context['GlobalPrevalence'] = self.global_prevalence

            if self.organization_first_seen:
                file_context['OrganizationFirstSeen'] = self.organization_first_seen

            if self.organization_last_seen:
                file_context['OrganizationLastSeen'] = self.organization_last_seen

            if self.first_seen_by_source:
                file_context['FirstSeenBySource'] = self.first_seen_by_source

            if self.last_seen_by_source:
                file_context['LastSeenBySource'] = self.last_seen_by_source

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                file_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                file_context['Relationships'] = relationships_context

            ret_value = {
                Common.File.CONTEXT_PATH: file_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value

    class CVE(Indicator):
        """
        CVE indicator class - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#cve
        :type id: ``str``
        :param id: The ID of the CVE, for example: "CVE-2015-1653".

        :type cvss: ``str``
        :param cvss: The CVSS of the CVE, for example: "10.0".

        :type published: ``str``
        :param published: The timestamp of when the CVE was published.

        :type modified: ``str``
        :param modified: The timestamp of when the CVE was last modified.

        :type description: ``str``
        :param description: A description of the CVE.

        :type relationships: ``list of EntityRelationship``
        :param relationships: List of relationships of the indicator.

        :type stix_id: ``str``
        :param stix_id: CVE sitx id.

        :type cvss_version: ``str``
        :param cvss_version: The CVE CVSS version used.

        :type cvss_score: ``str``
        :param cvss_score: The CVE CVSS Score.

        :type cvss_vector: ``str``
        :param cvss_vector: CVE full cvss vector.

        :type cvss_table: ``str``
        :param cvss_table: CVE CVSS Table used to fill the different parts of the vector.

        :type community_notes: ``str``
        :param community_notes: Community notes about the CVE.

        :type tags: ``str``
        :param tags: Tags attached to the CVE.

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol: The CVE tlp color.

        :type publications: ``str``
        :param publications: Unique system-assigned ID of the vulnerability evaluation logic

        :type dbot_score: ``DBotScore``
        :param dbot_score: If file has a score then create and set a DBotScore object

        :type vulnerable_products: ``CPE``
        :param vulnerable_products: A list of CPE objects

        :type vulnerable_configurations: ``CPE``
        :param vulnerable_configurations: A list of CPE objects

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'CVE(val.ID && val.ID == obj.ID)'

        def __init__(self, id, cvss, published, modified, description, relationships=None, stix_id=None,
                    cvss_version=None, cvss_score=None, cvss_vector=None, cvss_table=None, community_notes=None,
                    tags=None, traffic_light_protocol=None, dbot_score=None, publications=None,
                    vulnerable_products=None, vulnerable_configurations=None):

            # Main indicator value
            self.id = id

            # Core custom fields
            self.community_notes = community_notes
            self.cvss = cvss
            self.cvss_version = cvss_version
            self.cvss_score = cvss_score
            self.cvss_vector = cvss_vector
            self.cvss_table = cvss_table
            self.description = description
            self.modified = modified
            self.published = published
            self.stix_id = stix_id
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol
            self.publications = publications

            # XSOAR Fields
            self.relationships = relationships
            self.dbot_score = dbot_score if dbot_score else Common.DBotScore(indicator=id,
                                                                            indicator_type=DBotScoreType.CVE,
                                                                            integration_name=None,
                                                                            score=Common.DBotScore.NONE)

            # Core custom fields for CVE type
            self.vulnerable_products = vulnerable_products
            self.vulnerable_configurations = vulnerable_configurations

        def to_context(self):
            cve_context = {
                'ID': self.id,
                'CVSS': {},
            }

            if self.cvss:
                cve_context['CVSS']['Score'] = self.cvss

            elif self.cvss_score:
                cve_context['CVSS']['Score'] = self.cvss_score

            if self.cvss_version:
                cve_context['CVSS']['Version'] = self.cvss_version

            if self.cvss_vector:
                cve_context['CVSS']['Vector'] = self.cvss_vector

            if self.cvss_table:
                cve_context['CVSS']['Table'] = self.cvss_table

            if self.published:
                cve_context['Published'] = self.published

            if self.modified:
                cve_context['Modified'] = self.modified

            if self.description:
                cve_context['Description'] = self.description

            if self.stix_id:
                cve_context['STIXID'] = self.stix_id

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                cve_context['Relationships'] = relationships_context

            if self.community_notes:
                cve_context['CommunityNotes'] = self.create_context_table(self.community_notes)

            if self.tags:
                cve_context['Tags'] = self.tags

            if self.traffic_light_protocol:
                cve_context['TrafficLightProtocol'] = self.traffic_light_protocol

            ret_value = {
                Common.CVE.CONTEXT_PATH: cve_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            if self.publications:
                cve_context['Publications'] = self.create_context_table(self.publications)

            if self.vulnerable_products:
                cve_context['VulnerableProducts'] = self.create_context_table(self.vulnerable_products)

            if self.vulnerable_configurations:
                cve_context['VulnerableConfigurations'] = self.create_context_table(self.vulnerable_configurations)

            return ret_value

    class EMAIL(Indicator):
        """
        EMAIL indicator class

        :type address ``str``
        :param address: The email's address.

        :type domain: ``str``
        :param domain: The domain of the Email.

        :type blocked: ``bool``
        :param blocked: Whether the email address is blocked.

        :type relationships: ``list of EntityRelationship``
        :param relationships: List of relationships of the indicator.

        :type description: ``str``
        :param description: Description of the email address.

        :type internal: ``bool``
        :param internal: Is the email an internal address.

        :type stix_id: ``str``
        :param stix_id: The email assigned STIX ID.

        :type tags: ``str``
        :param tags: tags relevant to the email.

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol: The email address tlp color.

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'Account(val.Email.Address && val.Email.Address == obj.Email.Address)'

        def __init__(self, address, dbot_score, domain=None, blocked=None, relationships=None, description=None,
                    internal=None, stix_id=None, tags=None, traffic_light_protocol=None):
            # type (str, str, bool) -> None

            # Main indicator value
            self.address = address

            # Core custom fields
            self.blocked = blocked
            self.description = description
            self.internal = internal
            self.stix_id = stix_id
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol

            # Deprecated
            self.domain = domain

            # XSOAR Fields
            self.dbot_score = dbot_score
            self.relationships = relationships

        def to_context(self):
            email_context = {
                'Email': {'Address': self.address}
            }

            if self.blocked:
                email_context['Blocked'] = self.blocked

            if self.domain:
                email_context['Domain'] = self.domain

            if self.description:
                email_context['Description'] = self.description

            if self.internal:
                email_context['Internal'] = self.internal

            if self.stix_id:
                email_context['STIXID'] = self.stix_id

            if self.tags:
                email_context['Tags'] = self.tags

            if self.traffic_light_protocol:
                email_context['TrafficLightProtocol'] = self.traffic_light_protocol

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                email_context['Relationships'] = relationships_context

            ret_value = {
                Common.EMAIL.CONTEXT_PATH: email_context
            }
            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())
            return ret_value

    class URL(Indicator):
        """
        URL indicator - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#url
        :type url: ``str``
        :param url: The URL

        :type detection_engines: ``int``
        :param detection_engines: The total number of engines that checked the indicator.

        :type positive_detections: ``int``
        :param positive_detections: The number of engines that positively detected the indicator as malicious.

        :type category: ``str``
        :param category: The category associated with the indicator.

        :type feed_related_indicators: ``FeedRelatedIndicators``
        :param feed_related_indicators: List of indicators that are associated with the URL.

        :type malware_family: ``str``
        :param malware_family: The malware family associated with the URL.

        :type tags: ``str``
        :param tags: Tags of the URL.

        :type port: ``str``
        :param port: Ports that are associated with the URL.

        :type internal: ``bool``
        :param internal: Whether or not the URL is internal or external.

        :type campaign: ``str``
        :param campaign: The campaign associated with the URL.

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol: The Traffic Light Protocol (TLP) color that is suitable for the URL.

        :type threat_types: ``ThreatTypes``
        :param threat_types: Threat types that are associated with the file.

        :type asn: ``str``
        :param asn: The autonomous system name for the URL, for example: 'AS8948'.

        :type as_owner: ``str``
        :param as_owner: The autonomous system owner of the URL.

        :type geo_country: ``str``
        :param geo_country: The country in which the URL is located.

        :type organization: ``str``
        :param organization: The organization of the URL.

        :type community_notes: ``CommunityNotes``
        :param community_notes:  List of notes on the URL that were given by the community.

        :type publications: ``Publications``
        :param publications: List of publications on the URL that was published.

        :type relationships: ``list of EntityRelationship``
        :param relationships: List of relationships of the indicator.

        :type dbot_score: ``DBotScore``
        :param dbot_score: If URL has reputation then create DBotScore object

        :type blocked: ``bool``
        :param blocked: Is the URL blocked.

        :type certificates: ``Certificates``
        :param certificates: A list of certificates associated with the url.

        :type description: ``str``
        :param description: A description of the URL.

        :type stix_id: ``str``
        :param stix_id: The URL STIX ID.

        :type organization_prevalence: ``int``
        :param organization_prevalence: The number of times the indicator is detected in the organization.

        :type global_prevalence: ``int``
        :param global_prevalence: The number of times the indicator is detected across all organizations.

        :type organization_first_seen: ``str``
        :param organization_first_seen: ISO 8601 date time string; when the indicator was first seen in the organization.

        :type organization_last_seen: ``str``
        :param organization_last_seen: ISO 8601 date time string; the last time a specific organization encountered an indicator.

        :type first_seen_by_source: ``str``
        :param first_seen_by_source: ISO 8601 date time string; when the indicator was first seen by the source vendor.

        :type last_seen_by_source: ``str``
        :param last_seen_by_source: ISO 8601 date time string; when the indicator was last seen by the source vendor.

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'URL(val.Data && val.Data == obj.Data)'

        def __init__(self, url, dbot_score, detection_engines=None, positive_detections=None, category=None,
                    feed_related_indicators=None, tags=None, malware_family=None, port=None, internal=None,
                    campaign=None, traffic_light_protocol=None, threat_types=None, asn=None, as_owner=None,
                    geo_country=None, organization=None, community_notes=None, publications=None, relationships=None,
                    blocked=None, certificates=None, description=None, stix_id=None, organization_prevalence=None,
                    global_prevalence=None, organization_first_seen=None, organization_last_seen=None,
                    first_seen_by_source=None, last_seen_by_source=None):

            # Main indicator value
            self.url = url

            # Core custom fields
            self.blocked = blocked
            self.certificates = certificates
            self.community_notes = community_notes
            self.description = description
            self.internal = internal
            self.stix_id = stix_id
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol

            # Additional custom fields
            self.detection_engines = detection_engines
            self.positive_detections = positive_detections
            self.category = category
            self.feed_related_indicators = feed_related_indicators
            self.malware_family = malware_family
            self.port = port
            self.campaign = campaign
            self.threat_types = threat_types
            self.asn = asn
            self.as_owner = as_owner
            self.geo_country = geo_country
            self.organization = organization
            self.publications = publications
            self.organization_prevalence = organization_prevalence
            self.global_prevalence = global_prevalence
            self.organization_first_seen = organization_first_seen
            self.organization_last_seen = organization_last_seen
            self.first_seen_by_source = first_seen_by_source
            self.last_seen_by_source = last_seen_by_source

            # XSOAR Fields
            self.relationships = relationships
            self.dbot_score = dbot_score

        def to_context(self):
            url_context = {
                'Data': self.url
            }

            if self.blocked:
                url_context['Blocked'] = self.blocked

            if self.certificates:
                url_context['Certificates'] = self.create_context_table(self.certificates)

            if self.description:
                url_context['Description'] = self.description

            if self.stix_id:
                url_context['STIXID'] = self.stix_id

            if self.detection_engines is not None:
                url_context['DetectionEngines'] = self.detection_engines

            if self.positive_detections is not None:
                url_context['PositiveDetections'] = self.positive_detections

            if self.category:
                url_context['Category'] = self.category

            if self.feed_related_indicators:
                url_context['FeedRelatedIndicators'] = self.create_context_table(self.feed_related_indicators)

            if self.tags:
                url_context['Tags'] = self.tags

            if self.malware_family:
                url_context['MalwareFamily'] = self.malware_family

            if self.port:
                url_context['Port'] = self.port

            if self.internal:
                url_context['Internal'] = self.internal

            if self.campaign:
                url_context['Campaign'] = self.campaign

            if self.traffic_light_protocol:
                url_context['TrafficLightProtocol'] = self.traffic_light_protocol

            if self.threat_types:
                url_context['ThreatTypes'] = self.create_context_table(self.threat_types)

            if self.asn:
                url_context['ASN'] = self.asn

            if self.as_owner:
                url_context['ASOwner'] = self.as_owner

            if self.geo_country:
                url_context['Geo'] = {'Country': self.geo_country}

            if self.organization:
                url_context['Organization'] = self.organization

            if self.community_notes:
                url_context['CommunityNotes'] = self.create_context_table(self.community_notes)

            if self.publications:
                url_context['Publications'] = self.create_context_table(self.publications)

            if self.organization_prevalence is not None:  # checking for `is not None` to allow `0`-value
                url_context['OrganizationPrevalence'] = self.organization_prevalence

            if self.global_prevalence is not None:  # checking for `is not None` to allow `0`-value
                url_context['GlobalPrevalence'] = self.global_prevalence

            if self.organization_first_seen:
                url_context['OrganizationFirstSeen'] = self.organization_first_seen

            if self.organization_last_seen:
                url_context['OrganizationLastSeen'] = self.organization_last_seen

            if self.first_seen_by_source:
                url_context['FirstSeenBySource'] = self.first_seen_by_source

            if self.last_seen_by_source:
                url_context['LastSeenBySource'] = self.last_seen_by_source

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                url_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                url_context['Relationships'] = relationships_context

            ret_value = {
                Common.URL.CONTEXT_PATH: url_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value

    class Domain(Indicator):
        """ ignore docstring
        Domain indicator - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#domain

        :type whois_records: ``WhoisRecord``
        :param whois_records: List of whois records

        :type description: ``str``
        :param description: A description of the Domain.

        :type stix_id: ``str``
        :param stix_id: The domain STIX ID.

        :type blocked: ``bool``
        :param blocked: Is the domain blocked.

        :type certificates: ``Certificates``
        :param certificates: The certificates belonging to the domain.

        :type dns_records: ``DNSRecord``
        :param dns_records: A list of DNS records for the domain.

        :type organization_prevalence: ``int``
        :param organization_prevalence: The number of times the indicator is detected in the organization.

        :type global_prevalence: ``int``
        :param global_prevalence: The number of times the indicator is detected across all organizations.

        :type organization_first_seen: ``str``
        :param organization_first_seen: ISO 8601 date time string; when the indicator was first seen in the organization.

        :type organization_last_seen: ``str``
        :param organization_last_seen: ISO 8601 date time string; the last time a specific organization encountered an indicator.

        :type first_seen_by_source: ``str``
        :param first_seen_by_source: ISO 8601 date time string; when the indicator was first seen by the source vendor.

        :type last_seen_by_source: ``str``
        :param last_seen_by_source: ISO 8601 date time string; when the indicator was last seen by the source vendor.
        """
        CONTEXT_PATH = 'Domain(val.Name && val.Name == obj.Name)'

        def __init__(self, domain, dbot_score, dns=None, detection_engines=None, positive_detections=None,
                    organization=None, sub_domains=None, creation_date=None, updated_date=None, expiration_date=None,
                    domain_status=None, name_servers=None, feed_related_indicators=None, malware_family=None,
                    registrar_name=None, registrar_abuse_email=None, registrar_abuse_phone=None,
                    registrant_name=None, registrant_email=None, registrant_phone=None, registrant_country=None,
                    admin_name=None, admin_email=None, admin_phone=None, admin_country=None, tags=None,
                    domain_idn_name=None, port=None,
                    internal=None, category=None, campaign=None, traffic_light_protocol=None, threat_types=None,
                    community_notes=None, publications=None, geo_location=None, geo_country=None, geo_description=None,
                    tech_country=None, tech_name=None, tech_email=None, tech_organization=None, billing=None,
                    whois_records=None, relationships=None, description=None, stix_id=None, blocked=None,
                    certificates=None, dns_records=None, rank=None, organization_prevalence=None,
                    global_prevalence=None, organization_first_seen=None, organization_last_seen=None,
                    first_seen_by_source=None, last_seen_by_source=None):

            # Main indicator value
            self.domain = domain

            # Core custom fields
            self.blocked = blocked
            self.certificates = certificates
            self.community_notes = community_notes
            self.creation_date = creation_date
            self.description = description
            self.dns_records = dns_records
            self.expiration_date = expiration_date
            self.internal = internal
            self.stix_id = stix_id
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol
            self.whois_records = whois_records

            # Additional custom fields
            self.dns = dns
            self.detection_engines = detection_engines
            self.positive_detections = positive_detections
            self.organization = organization
            self.sub_domains = sub_domains
            self.updated_date = updated_date
            self.rank = rank

            # Whois related records - Registrar
            self.registrar_name = registrar_name
            self.registrar_abuse_email = registrar_abuse_email
            self.registrar_abuse_phone = registrar_abuse_phone

            self.registrant_name = registrant_name
            self.registrant_email = registrant_email
            self.registrant_phone = registrant_phone
            self.registrant_country = registrant_country

            self.admin_name = admin_name
            self.admin_email = admin_email
            self.admin_phone = admin_phone
            self.admin_country = admin_country

            self.tech_country = tech_country
            self.tech_name = tech_name
            self.tech_organization = tech_organization
            self.tech_email = tech_email
            self.billing = billing

            # Additional custom records (non core)
            self.domain_status = domain_status
            self.name_servers = name_servers
            self.feed_related_indicators = feed_related_indicators
            self.malware_family = malware_family
            self.domain_idn_name = domain_idn_name
            self.port = port
            self.category = category
            self.campaign = campaign
            self.threat_types = threat_types
            self.publications = publications
            self.geo_location = geo_location
            self.geo_country = geo_country
            self.geo_description = geo_description
            self.organization_prevalence = organization_prevalence
            self.global_prevalence = global_prevalence
            self.organization_first_seen = organization_first_seen
            self.organization_last_seen = organization_last_seen
            self.first_seen_by_source = first_seen_by_source
            self.last_seen_by_source = last_seen_by_source

            # XSOAR Fields
            self.relationships = relationships
            self.dbot_score = dbot_score

        def to_context(self):
            domain_context = {
                'Name': self.domain
            }
            whois_context = {}

            if self.dns:
                domain_context['DNS'] = self.dns

            if self.detection_engines is not None:
                domain_context['DetectionEngines'] = self.detection_engines

            if self.positive_detections is not None:
                domain_context['PositiveDetections'] = self.positive_detections

            if self.registrar_name or self.registrar_abuse_email or self.registrar_abuse_phone:
                domain_context['Registrar'] = {
                    'Name': self.registrar_name,
                    'AbuseEmail': self.registrar_abuse_email,
                    'AbusePhone': self.registrar_abuse_phone
                }
                whois_context['Registrar'] = domain_context['Registrar']

            if self.registrant_name or self.registrant_phone or self.registrant_email or self.registrant_country:
                domain_context['Registrant'] = {
                    'Name': self.registrant_name,
                    'Email': self.registrant_email,
                    'Phone': self.registrant_phone,
                    'Country': self.registrant_country
                }
                whois_context['Registrant'] = domain_context['Registrant']

            if self.admin_name or self.admin_email or self.admin_phone or self.admin_country:
                domain_context['Admin'] = {
                    'Name': self.admin_name,
                    'Email': self.admin_email,
                    'Phone': self.admin_phone,
                    'Country': self.admin_country
                }
                whois_context['Admin'] = domain_context['Admin']

            if self.organization:
                domain_context['Organization'] = self.organization

            if self.sub_domains:
                domain_context['Subdomains'] = self.sub_domains

            if self.domain_status:
                domain_context['DomainStatus'] = self.domain_status
                whois_context['DomainStatus'] = domain_context['DomainStatus']

            if self.creation_date:
                domain_context['CreationDate'] = self.creation_date
                whois_context['CreationDate'] = domain_context['CreationDate']

            if self.updated_date:
                domain_context['UpdatedDate'] = self.updated_date
                whois_context['UpdatedDate'] = domain_context['UpdatedDate']

            if self.expiration_date:
                domain_context['ExpirationDate'] = self.expiration_date
                whois_context['ExpirationDate'] = domain_context['ExpirationDate']

            if self.name_servers:
                domain_context['NameServers'] = self.name_servers
                whois_context['NameServers'] = domain_context['NameServers']

            if self.tags:
                domain_context['Tags'] = self.tags

            if self.feed_related_indicators:
                domain_context['FeedRelatedIndicators'] = self.create_context_table(self.feed_related_indicators)

            if self.whois_records:
                domain_context['WhoisRecords'] = self.create_context_table(self.whois_records)

            if self.malware_family:
                domain_context['MalwareFamily'] = self.malware_family

            if self.organization_prevalence is not None:  # checking for `is not None` to allow `0`-value
                domain_context['OrganizationPrevalence'] = self.organization_prevalence

            if self.global_prevalence is not None:  # checking for `is not None` to allow `0`-value
                domain_context['GlobalPrevalence'] = self.global_prevalence

            if self.organization_first_seen:
                domain_context['OrganizationFirstSeen'] = self.organization_first_seen

            if self.organization_last_seen:
                domain_context['OrganizationLastSeen'] = self.organization_last_seen

            if self.first_seen_by_source:
                domain_context['FirstSeenBySource'] = self.first_seen_by_source

            if self.last_seen_by_source:
                domain_context['LastSeenBySource'] = self.last_seen_by_source

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                domain_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            if self.domain_idn_name:
                domain_context['DomainIDNName'] = self.domain_idn_name

            if self.port:
                domain_context['Port'] = self.port

            if self.internal:
                domain_context['Internal'] = self.internal

            if self.category:
                domain_context['Category'] = self.category

            if self.campaign:
                domain_context['Campaign'] = self.campaign

            if self.traffic_light_protocol:
                domain_context['TrafficLightProtocol'] = self.traffic_light_protocol

            if self.threat_types:
                domain_context['ThreatTypes'] = self.create_context_table(self.threat_types)

            if self.community_notes:
                domain_context['CommunityNotes'] = self.create_context_table(self.community_notes)

            if self.publications:
                domain_context['Publications'] = self.create_context_table(self.publications)

            if self.geo_location or self.geo_country or self.geo_description:
                domain_context['Geo'] = {}
                if self.geo_location:
                    domain_context['Geo']['Location'] = self.geo_location
                if self.geo_country:
                    domain_context['Geo']['Country'] = self.geo_country
                if self.geo_description:
                    domain_context['Geo']['Description'] = self.geo_description

            if self.tech_country or self.tech_name or self.tech_organization or self.tech_email:
                domain_context['Tech'] = {}
                if self.tech_country:
                    domain_context['Tech']['Country'] = self.tech_country
                if self.tech_name:
                    domain_context['Tech']['Name'] = self.tech_name
                if self.tech_organization:
                    domain_context['Tech']['Organization'] = self.tech_organization
                if self.tech_email:
                    domain_context['Tech']['Email'] = self.tech_email

            if self.billing:
                domain_context['Billing'] = self.billing

            if whois_context:
                domain_context['WHOIS'] = whois_context

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                domain_context['Relationships'] = relationships_context

            ret_value = {
                Common.Domain.CONTEXT_PATH: domain_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            if self.dns_records:
                domain_context['DNSRecords'] = self.create_context_table(self.dns_records)

            if self.stix_id:
                domain_context['STIXID'] = self.stix_id

            if self.description:
                domain_context['Description'] = self.description

            if self.stix_id:
                domain_context['Blocked'] = self.blocked

            if self.certificates:
                domain_context['Certificates'] = self.create_context_table(self.certificates)

            if self.rank:
                domain_context['Rank'] = self.create_context_table(self.rank)

            return ret_value

    class Endpoint(Indicator):
        """ ignore docstring
        Endpoint indicator - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#endpoint
        """
        # Compare by both ID and Vendor if both exist, otherwise just by ID.
        CONTEXT_PATH = 'Endpoint(val.ID && val.ID == obj.ID && val.Vendor == obj.Vendor)'

        def __init__(self, id, hostname=None, ip_address=None, domain=None, mac_address=None,
                    os=None, os_version=None, dhcp_server=None, bios_version=None, model=None,
                    memory=None, processors=None, processor=None, relationships=None, vendor=None, status=None,
                    is_isolated=None):
            self.id = id
            self.hostname = hostname
            self.ip_address = ip_address
            self.domain = domain
            self.mac_address = mac_address
            self.os = os
            self.os_version = os_version
            self.dhcp_server = dhcp_server
            self.bios_version = bios_version
            self.model = model
            self.memory = memory
            self.processors = processors
            self.processor = processor
            self.vendor = vendor
            self.status = status
            self.is_isolated = is_isolated
            self.relationships = relationships

        def to_context(self):
            endpoint_context = {
                'ID': self.id
            }

            if self.hostname:
                endpoint_context['Hostname'] = self.hostname

            if self.ip_address:
                endpoint_context['IPAddress'] = self.ip_address

            if self.domain:
                endpoint_context['Domain'] = self.domain

            if self.mac_address:
                endpoint_context['MACAddress'] = self.mac_address

            if self.os:
                endpoint_context['OS'] = self.os

            if self.os_version:
                endpoint_context['OSVersion'] = self.os_version

            if self.dhcp_server:
                endpoint_context['DHCPServer'] = self.dhcp_server

            if self.bios_version:
                endpoint_context['BIOSVersion'] = self.bios_version

            if self.model:
                endpoint_context['Model'] = self.model

            if self.memory:
                endpoint_context['Memory'] = self.memory

            if self.processors:
                endpoint_context['Processors'] = self.processors

            if self.processor:
                endpoint_context['Processor'] = self.processor

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                endpoint_context['Relationships'] = relationships_context

            if self.vendor:
                endpoint_context['Vendor'] = self.vendor

            if self.status:
                if self.status not in ENDPOINT_STATUS_OPTIONS:
                    raise ConnectorError('Status does not have a valid value such as: Online or Offline')
                endpoint_context['Status'] = self.status

            if self.is_isolated:
                if self.is_isolated not in ENDPOINT_ISISOLATED_OPTIONS:
                    raise ConnectorError('Is Isolated does not have a valid value such as: Yes, No, Pending'
                                    ' isolation or Pending unisolation')
                endpoint_context['IsIsolated'] = self.is_isolated

            ret_value = {
                Common.Endpoint.CONTEXT_PATH: endpoint_context
            }

            return ret_value

    class Account(Indicator):
        """
        Account indicator - https://xsoar.pan.dev/docs/integrations/context-standards-recommended#account

        :type blocked: ``boolean``
        :param blocked: Is the indicator blocked.

        :type community_notes: ``CommunityNotes``
        :param community_notes: Notes on the Account that were given by the community.

        :type dbot_score: ``DBotScore``
        :param dbot_score: If account has reputation then create DBotScore object

        :type creation_date: ``str``
        :param creation_date: The date the account was created

        :type description: ``str``
        :param description: Description of the account

        :type stix_id: ``str``
        :param stix_id: STIX ID for the account

        :type tags: ``str``
        :param tags: List of tags related to the account.

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol: The account indicator tlp color

        :type user_id: ``str``
        :param user_id: The account associated user id.

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'Account(val.id && val.id == obj.id)'

        def __init__(self, id=None, type=None, username=None, display_name=None, groups=None,
                    domain=None, email_address=None, telephone_number=None, office=None, job_title=None,
                    department=None, country=None, state=None, city=None, street=None, is_enabled=None,
                    dbot_score=None, relationships=None, blocked=None, community_notes=None, creation_date=None,
                    description=None, stix_id=None, tags=None, traffic_light_protocol=None, user_id=None,
                    manager_email=None, manager_display_name=None, risk_level=None, **kwargs):

            self.id = id
            self.type = type
            self.blocked = blocked
            self.community_notes = community_notes
            self.creation_date = creation_date
            self.description = description
            self.stix_id = stix_id
            self.username = username
            self.display_name = display_name
            self.groups = groups
            self.domain = domain
            self.email_address = email_address
            self.telephone_number = telephone_number
            self.office = office
            self.job_title = job_title
            self.department = department
            self.country = country
            self.state = state
            self.city = city
            self.street = street
            self.is_enabled = is_enabled
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol
            self.user_id = user_id
            self.relationships = relationships
            self.manager_email_address = manager_email
            self.manager_display_name = manager_display_name
            self.risk_level = risk_level
            self.kwargs = kwargs

            if dbot_score and not isinstance(dbot_score, Common.DBotScore):
                raise ConnectorError('dbot_score must be of type DBotScore')

            self.dbot_score = dbot_score

        def to_context(self):
            account_context = {}

            if self.id:
                account_context['ID'] = self.id

            if self.type:
                account_context['Type'] = self.type

            if self.blocked:
                account_context['Blocked'] = self.blocked

            if self.creation_date:
                account_context['CreationDate'] = self.creation_date

            irrelevent = ['CONTEXT_PATH', 'to_context', 'dbot_score', 'id', 'create_context_table', 'kwargs']
            details = [detail for detail in dir(self) if not detail.startswith('__') and detail not in irrelevent]

            for detail in details:
                if self.__getattribute__(detail) is not None:
                    if detail == 'email_address':
                        account_context['Email'] = {
                            'Address': self.email_address
                        }
                    elif detail in ('manager_email_address', 'manager_display_name'):
                        if 'Manager' not in account_context:
                            account_context['Manager'] = {}
                        if detail == 'manager_email_address':
                            account_context['Manager']['Email'] = self.manager_email_address
                        elif detail == 'manager_display_name':
                            account_context['Manager']['DisplayName'] = self.manager_display_name
                    else:
                        Detail = camelize_string(detail, '_')
                        account_context[Detail] = self.__getattribute__(detail)

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                account_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            if self.relationships:
                relationships_context = [relationship.to_context() for relationship in self.relationships if
                                        relationship.to_context()]
                account_context['Relationships'] = relationships_context

            if self.community_notes:
                account_context['CommunityNotes'] = self.create_context_table(self.community_notes)

            if self.kwargs:
                for key, value in self.kwargs.items():
                    if key not in account_context:
                        account_context[key] = value
                    else:
                        logger.debug(
                            'Skipping the addition of the "{key}" key to the account context as it already exists.'.format(
                                key=key)
                        )

            ret_value = {
                Common.Account.CONTEXT_PATH: account_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value

    class Cryptocurrency(Indicator):
        """
        Cryptocurrency indicator - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#cryptocurrency
        :type address: ``str``
        :param address: The Cryptocurrency address

        :type address_type: ``str``
        :param address_type: The Cryptocurrency type - e.g. `bitcoin`.

        :type dbot_score: ``DBotScore``
        :param dbot_score:  If the address has reputation then create DBotScore object.

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'Cryptocurrency(val.Address && val.Address == obj.Address)'

        def __init__(self, address, address_type, dbot_score):
            self.address = address
            self.address_type = address_type

            self.dbot_score = dbot_score

        def to_context(self):
            crypto_context = {
                'Address': self.address,
                'AddressType': self.address_type
            }

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                crypto_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            ret_value = {
                Common.Cryptocurrency.CONTEXT_PATH: crypto_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value

    class AttackPattern(Indicator):
        """
        Attack Pattern indicator

        :type stix_id: ``str``
        :param stix_id: The Attack Pattern STIX ID

        :type kill_chain_phases: ``str``
        :param kill_chain_phases: The Attack Pattern kill chain phases.

        :type first_seen_by_source: ``str``
        :param first_seen_by_source: The Attack Pattern first seen by source

        :type description: ``str``
        :param description: The Attack Pattern description

        :type operating_system_refs: ``str``
        :param operating_system_refs: The operating system refs of the Attack Pattern.

        :type publications: ``str``
        :param publications: The Attack Pattern publications

        :type mitre_id: ``str``
        :param mitre_id: The Attack Pattern kill mitre id.

        :type tags: ``str``
        :param tags: The Attack Pattern kill tags.

        :type dbot_score: ``DBotScore``
        :param dbot_score:  If the address has reputation then create DBotScore object.

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol: The Traffic Light Protocol (TLP) color that is suitable for the AP.

        :type community_notes: ``CommunityNotes``
        :param community_notes:  A list of community notes for the AP.

        :type external_references: ``ExternalReference``
        :param external_references:  A list of id's and description of the AP via external refs.

        :type value: ``str``
        :param value: The Attack Pattern value (name) - example: "Plist File Modification"

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'AttackPattern(val.value && val.value == obj.value)'

        def __init__(self, stix_id, kill_chain_phases=None, first_seen_by_source=None, description=None,
                    operating_system_refs=None, publications=None, mitre_id=None, tags=None,
                    traffic_light_protocol=None, dbot_score=None, community_notes=None, external_references=None, value=None):

            self.community_notes = community_notes
            self.description = description
            self.external_references = external_references
            self.first_seen_by_source = first_seen_by_source
            self.kill_chain_phases = kill_chain_phases
            self.mitre_id = mitre_id
            self.operating_system_refs = operating_system_refs
            self.publications = publications
            self.stix_id = stix_id
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol
            self.value = value
            self.dbot_score = dbot_score

        def to_context(self):
            attack_pattern_context = {
                'STIXID': self.stix_id,
                "KillChainPhases": self.kill_chain_phases,
                "FirstSeenBySource": self.first_seen_by_source,
                'OperatingSystemRefs': self.operating_system_refs,
                "Publications": self.publications,
                "MITREID": self.mitre_id,
                "Value": self.value,
                "Tags": self.tags,
                "Description": self.description
            }

            if self.external_references:
                attack_pattern_context['ExternalReferences'] = self.create_context_table(self.external_references)

            if self.traffic_light_protocol:
                attack_pattern_context['TrafficLightProtocol'] = self.traffic_light_protocol

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                attack_pattern_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            ret_value = {
                Common.AttackPattern.CONTEXT_PATH: attack_pattern_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value

    class CertificatePublicKey(object):
        """
        CertificatePublicKey class
        Defines an X509  PublicKey used in Common.Certificate

        :type algorithm: ``str``
        :param algorithm: The encryption algorithm: DSA, RSA, EC or UNKNOWN (Common.CertificatePublicKey.Algorithm enum)

        :type length: ``int``
        :param length: The length of the public key

        :type publickey: ``Optional[str]``
        :param publickey: publickey

        :type p: ``Optional[str]``
        :param p: P parameter used in DSA algorithm

        :type q: ``Optional[str]``
        :param q: Q parameter used in DSA algorithm

        :type g: ``Optional[str]``
        :param g: G parameter used in DSA algorithm

        :type modulus: ``Optional[str]``
        :param modulus: modulus parameter used in RSA algorithm

        :type modulus: ``Optional[int]``
        :param modulus: exponent parameter used in RSA algorithm

        :type x: ``Optional[str]``
        :param x: X parameter used in EC algorithm

        :type y: ``Optional[str]``
        :param y: Y parameter used in EC algorithm

        :type curve: ``Optional[str]``
        :param curve: curve parameter used in EC algorithm

        :return: None
        :rtype: ``None``
        """

        class Algorithm(object):
            """
            Algorithm class to enumerate available algorithms

            :return: None
            :rtype: ``None``
            """
            DSA = "DSA"
            RSA = "RSA"
            EC = "EC"
            UNKNOWN = "Unknown Algorithm"

            @staticmethod
            def is_valid_type(_type):
                return _type in (
                    Common.CertificatePublicKey.Algorithm.DSA,
                    Common.CertificatePublicKey.Algorithm.RSA,
                    Common.CertificatePublicKey.Algorithm.EC,
                    Common.CertificatePublicKey.Algorithm.UNKNOWN
                )

        def __init__(
            self,
            algorithm,  # type: str
            length,  # type: int
            publickey=None,  # type: str
            p=None,  # type: str
            q=None,  # type: str
            g=None,  # type: str
            modulus=None,  # type: str
            exponent=None,  # type: int
            x=None,  # type: str
            y=None,  # type: str
            curve=None  # type: str
        ):

            if not Common.CertificatePublicKey.Algorithm.is_valid_type(algorithm):
                raise ConnectorError('algorithm must be of type Common.CertificatePublicKey.Algorithm enum')

            self.algorithm = algorithm
            self.length = length
            self.publickey = publickey
            self.p = p
            self.q = q
            self.g = g
            self.modulus = modulus
            self.exponent = exponent
            self.x = x
            self.y = y
            self.curve = curve

        def to_context(self):
            publickey_context = {
                'Algorithm': self.algorithm,
                'Length': self.length
            }

            if self.publickey:
                publickey_context['PublicKey'] = self.publickey

            if self.algorithm == Common.CertificatePublicKey.Algorithm.DSA:
                if self.p:
                    publickey_context['P'] = self.p
                if self.q:
                    publickey_context['Q'] = self.q
                if self.g:
                    publickey_context['G'] = self.g

            elif self.algorithm == Common.CertificatePublicKey.Algorithm.RSA:
                if self.modulus:
                    publickey_context['Modulus'] = self.modulus
                if self.exponent:
                    publickey_context['Exponent'] = self.exponent

            elif self.algorithm == Common.CertificatePublicKey.Algorithm.EC:
                if self.x:
                    publickey_context['X'] = self.x
                if self.y:
                    publickey_context['Y'] = self.y
                if self.curve:
                    publickey_context['Curve'] = self.curve

            elif self.algorithm == Common.CertificatePublicKey.Algorithm.UNKNOWN:
                pass

            return publickey_context

    class GeneralName(object):
        """
        GeneralName class
        Implements GeneralName interface from rfc5280
        Enumerates the available General Name Types

        :type gn_type: ``str``
        :param gn_type: General Name Type

        :type gn_value: ``str``
        :param gn_value: General Name Value

        :return: None
        :rtype: ``None``
        """
        OTHERNAME = 'otherName'
        RFC822NAME = 'rfc822Name'
        DNSNAME = 'dNSName'
        DIRECTORYNAME = 'directoryName'
        UNIFORMRESOURCEIDENTIFIER = 'uniformResourceIdentifier'
        IPADDRESS = 'iPAddress'
        REGISTEREDID = 'registeredID'

        @staticmethod
        def is_valid_type(_type):
            return _type in (
                Common.GeneralName.OTHERNAME,
                Common.GeneralName.RFC822NAME,
                Common.GeneralName.DNSNAME,
                Common.GeneralName.DIRECTORYNAME,
                Common.GeneralName.UNIFORMRESOURCEIDENTIFIER,
                Common.GeneralName.IPADDRESS,
                Common.GeneralName.REGISTEREDID
            )

        def __init__(
            self,
            gn_value,  # type: str
            gn_type  # type: str
        ):
            if not Common.GeneralName.is_valid_type(gn_type):
                raise ConnectorError(
                    'gn_type must be of type Common.GeneralName enum'
                )
            self.gn_type = gn_type
            self.gn_value = gn_value

        def to_context(self):
            return {
                'Type': self.gn_type,
                'Value': self.gn_value
            }

        def get_value(self):
            return self.gn_value

    class CertificateExtension(object):
        """
        CertificateExtension class
        Defines an X509 Certificate Extensions used in Common.Certificate


        :type extension_type: ``str``
        :param extension_type: The type of Extension (from Common.CertificateExtension.ExtensionType enum, or "Other)

        :type critical: ``bool``
        :param critical: Whether the extension is marked as critical

        :type extension_name: ``Optional[str]``
        :param extension_name: Name of the extension

        :type oid: ``Optional[str]``
        :param oid: OID of the extension

        :type subject_alternative_names: ``Optional[List[Common.CertificateExtension.SubjectAlternativeName]]``
        :param subject_alternative_names: Subject Alternative Names

        :type authority_key_identifier: ``Optional[Common.CertificateExtension.AuthorityKeyIdentifier]``
        :param authority_key_identifier: Authority Key Identifier

        :type digest: ``Optional[str]``
        :param digest: digest for Subject Key Identifier extension

        :type digital_signature: ``Optional[bool]``
        :param digital_signature: Digital Signature usage for Key Usage extension

        :type content_commitment: ``Optional[bool]``
        :param content_commitment: Content Commitment usage for Key Usage extension

        :type key_encipherment: ``Optional[bool]``
        :param key_encipherment: Key Encipherment usage for Key Usage extension

        :type data_encipherment: ``Optional[bool]``
        :param data_encipherment: Data Encipherment usage for Key Usage extension

        :type key_agreement: ``Optional[bool]``
        :param key_agreement: Key Agreement usage for Key Usage extension

        :type key_cert_sign: ``Optional[bool]``
        :param key_cert_sign: Key Cert Sign usage for Key Usage extension

        :type usages: ``Optional[List[str]]``
        :param usages: Usages for Extended Key Usage extension

        :type distribution_points: ``Optional[List[Common.CertificateExtension.DistributionPoint]]``
        :param distribution_points: Distribution Points

        :type certificate_policies: ``Optional[List[Common.CertificateExtension.CertificatePolicy]]``
        :param certificate_policies: Certificate Policies

        :type authority_information_access: ``Optional[List[Common.CertificateExtension.AuthorityInformationAccess]]``
        :param authority_information_access: Authority Information Access

        :type basic_constraints: ``Optional[Common.CertificateExtension.BasicConstraints]``
        :param basic_constraints: Basic Constraints

        :type signed_certificate_timestamps: ``Optional[List[Common.CertificateExtension.SignedCertificateTimestamp]]``
        :param signed_certificate_timestamps: (PreCertificate)Signed Certificate Timestamps

        :type value: ``Optional[Union[str, List[Any], Dict[str, Any]]]``
        :param value: Raw value of the Extension (used for "Other" type)

        :return: None
        :rtype: ``None``
        """

        class SubjectAlternativeName(object):
            """
            SubjectAlternativeName class
            Implements Subject Alternative Name extension interface

            :type gn: ``Optional[Common.GeneralName]``
            :param gn: General Name Type provided as Common.GeneralName

            :type gn_type: ``Optional[str]``
            :param gn_type: General Name Type provided as string

            :type gn_value: ``Optional[str]``
            :param gn_value: General Name Value provided as string

            :return: None
            :rtype: ``None``
            """

            def __init__(
                self,
                gn=None,  # type: Optional[Common.GeneralName]
                gn_type=None,  # type: Optional[str]
                gn_value=None  # type: Optional[str]
            ):
                if gn:
                    self.gn = gn
                elif gn_type and gn_value:
                    self.gn = Common.GeneralName(
                        gn_value=gn_value,
                        gn_type=gn_type
                    )
                else:
                    raise ConnectorError('either GeneralName or gn_type/gn_value required to inizialize SubjectAlternativeName')

            def to_context(self):
                return self.gn.to_context()

            def get_value(self):
                return self.gn.get_value()

        class AuthorityKeyIdentifier(object):
            """
            AuthorityKeyIdentifier class
            Implements Authority Key Identifier extension interface

            :type issuer: ``Optional[List[Common.GeneralName]]``
            :param issuer: Issuer list

            :type serial_number: ``Optional[str]``
            :param serial_number: Serial Number

            :type key_identifier: ``Optional[str]``
            :param key_identifier: Key Identifier

            :return: None
            :rtype: ``None``
            """

            def __init__(
                self,
                issuer=None,  # type: Optional[List[Common.GeneralName]]
                serial_number=None,  # type: Optional[str]
                key_identifier=None  # type: Optional[str]
            ):
                self.issuer = issuer
                self.serial_number = serial_number
                self.key_identifier = key_identifier

            def to_context(self):
                authority_key_identifier_context = {}  # type: Dict[str, Any]

                if self.issuer:
                    authority_key_identifier_context['Issuer'] = self.issuer,

                if self.serial_number:
                    authority_key_identifier_context["SerialNumber"] = self.serial_number
                if self.key_identifier:
                    authority_key_identifier_context["KeyIdentifier"] = self.key_identifier

                return authority_key_identifier_context

        class DistributionPoint(object):
            """
            DistributionPoint class
            Implements Distribution Point extension interface

            :type full_name: ``Optional[List[Common.GeneralName]]``
            :param full_name: Full Name list

            :type relative_name: ``Optional[str]``
            :param relative_name: Relative Name

            :type crl_issuer: ``Optional[List[Common.GeneralName]]``
            :param crl_issuer: CRL Issuer

            :type reasons: ``Optional[List[str]]``
            :param reasons: Reason list

            :return: None
            :rtype: ``None``
            """

            def __init__(
                self,
                full_name=None,  # type: Optional[List[Common.GeneralName]]
                relative_name=None,  # type:  Optional[str]
                crl_issuer=None,  # type: Optional[List[Common.GeneralName]]
                reasons=None  # type: Optional[List[str]]
            ):
                self.full_name = full_name
                self.relative_name = relative_name
                self.crl_issuer = crl_issuer
                self.reasons = reasons

            def to_context(self):
                distribution_point_context = {}  # type: Dict[str, Union[List, str]]
                if self.full_name:
                    distribution_point_context["FullName"] = [fn.to_context() for fn in self.full_name]
                if self.relative_name:
                    distribution_point_context["RelativeName"] = self.relative_name
                if self.crl_issuer:
                    distribution_point_context["CRLIssuer"] = [ci.to_context() for ci in self.crl_issuer]
                if self.reasons:
                    distribution_point_context["Reasons"] = self.reasons

                return distribution_point_context

        class CertificatePolicy(object):
            """
            CertificatePolicy class
            Implements Certificate Policy extension interface

            :type policy_identifier: ``str``
            :param policy_identifier: Policy Identifier

            :type policy_qualifiers: ``Optional[List[str]]``
            :param policy_qualifiers: Policy Qualifier list

            :return: None
            :rtype: ``None``
            """

            def __init__(
                self,
                policy_identifier,  # type: str
                policy_qualifiers=None  # type: Optional[List[str]]
            ):
                self.policy_identifier = policy_identifier
                self.policy_qualifiers = policy_qualifiers

            def to_context(self):
                certificate_policies_context = {
                    "PolicyIdentifier": self.policy_identifier
                }  # type: Dict[str, Union[List, str]]

                if self.policy_qualifiers:
                    certificate_policies_context["PolicyQualifiers"] = self.policy_qualifiers

                return certificate_policies_context

        class AuthorityInformationAccess(object):
            """
            AuthorityInformationAccess class
            Implements Authority Information Access extension interface

            :type access_method: ``str``
            :param access_method: Access Method

            :type access_location: ``Common.GeneralName``
            :param access_location: Access Location

            :return: None
            :rtype: ``None``
            """

            def __init__(
                self,
                access_method,  # type: str
                access_location  # type: Common.GeneralName
            ):
                self.access_method = access_method
                self.access_location = access_location

            def to_context(self):
                return {
                    "AccessMethod": self.access_method,
                    "AccessLocation": self.access_location.to_context()
                }

        class BasicConstraints(object):
            """
            BasicConstraints class
            Implements Basic Constraints extension interface

            :type ca: ``bool``
            :param ca: Certificate Authority

            :type path_length: ``int``
            :param path_length: Path Length

            :return: None
            :rtype: ``None``
            """

            def __init__(
                self,
                ca,  # type: bool
                path_length=None  # type: int
            ):
                self.ca = ca
                self.path_length = path_length

            def to_context(self):
                basic_constraints_context = {
                    "CA": self.ca
                }  # type: Dict[str, Union[str, int]]

                if self.path_length:
                    basic_constraints_context["PathLength"] = self.path_length

                return basic_constraints_context

        class SignedCertificateTimestamp(object):
            """
            SignedCertificateTimestamp class
            Implementsinterface for  "SignedCertificateTimestamp" extensions

            :type entry_type: ``str``
            :param entry_type: Entry Type (from Common.CertificateExtension.SignedCertificateTimestamp.EntryType enum)

            :type version: ``str``
            :param version: Version

            :type log_id: ``str``
            :param log_id: Log ID

            :type timestamp: ``str``
            :param timestamp: Timestamp (ISO8601 string representation in UTC)

            :return: None
            :rtype: ``None``
            """

            class EntryType(object):
                """
                EntryType class
                Enumerates Entry Types for SignedCertificateTimestamp class

                :return: None
                :rtype: ``None``
                """
                PRECERTIFICATE = "PreCertificate"
                X509CERTIFICATE = "X509Certificate"

                @staticmethod
                def is_valid_type(_type):
                    return _type in (
                        Common.CertificateExtension.SignedCertificateTimestamp.EntryType.PRECERTIFICATE,
                        Common.CertificateExtension.SignedCertificateTimestamp.EntryType.X509CERTIFICATE
                    )

            def __init__(
                self,
                entry_type,  # type: str
                version,  # type: int
                log_id,  # type: str
                timestamp  # type: str
            ):
                if not Common.CertificateExtension.SignedCertificateTimestamp.EntryType.is_valid_type(entry_type):
                    raise ConnectorError(
                        'entry_type must be of type Common.CertificateExtension.SignedCertificateTimestamp.EntryType enum'
                    )

                self.entry_type = entry_type
                self.version = version
                self.log_id = log_id
                self.timestamp = timestamp

            def to_context(self):
                timestamps_context = {}  # type: Dict[str, Any]

                timestamps_context['Version'] = self.version
                timestamps_context["LogId"] = self.log_id
                timestamps_context["Timestamp"] = self.timestamp
                timestamps_context["EntryType"] = self.entry_type

                return timestamps_context

        class ExtensionType(object):
            """
            ExtensionType class
            Enumerates Extension Types for Common.CertificatExtension class

            :return: None
            :rtype: ``None``
            """
            SUBJECTALTERNATIVENAME = "SubjectAlternativeName"
            AUTHORITYKEYIDENTIFIER = "AuthorityKeyIdentifier"
            SUBJECTKEYIDENTIFIER = "SubjectKeyIdentifier"
            KEYUSAGE = "KeyUsage"
            EXTENDEDKEYUSAGE = "ExtendedKeyUsage"
            CRLDISTRIBUTIONPOINTS = "CRLDistributionPoints"
            CERTIFICATEPOLICIES = "CertificatePolicies"
            AUTHORITYINFORMATIONACCESS = "AuthorityInformationAccess"
            BASICCONSTRAINTS = "BasicConstraints"
            SIGNEDCERTIFICATETIMESTAMPS = "SignedCertificateTimestamps"
            PRESIGNEDCERTIFICATETIMESTAMPS = "PreCertSignedCertificateTimestamps"
            OTHER = "Other"

            @staticmethod
            def is_valid_type(_type):
                return _type in (
                    Common.CertificateExtension.ExtensionType.SUBJECTALTERNATIVENAME,
                    Common.CertificateExtension.ExtensionType.AUTHORITYKEYIDENTIFIER,
                    Common.CertificateExtension.ExtensionType.SUBJECTKEYIDENTIFIER,
                    Common.CertificateExtension.ExtensionType.KEYUSAGE,
                    Common.CertificateExtension.ExtensionType.EXTENDEDKEYUSAGE,
                    Common.CertificateExtension.ExtensionType.CRLDISTRIBUTIONPOINTS,
                    Common.CertificateExtension.ExtensionType.CERTIFICATEPOLICIES,
                    Common.CertificateExtension.ExtensionType.AUTHORITYINFORMATIONACCESS,
                    Common.CertificateExtension.ExtensionType.BASICCONSTRAINTS,
                    Common.CertificateExtension.ExtensionType.SIGNEDCERTIFICATETIMESTAMPS,
                    Common.CertificateExtension.ExtensionType.PRESIGNEDCERTIFICATETIMESTAMPS,
                    Common.CertificateExtension.ExtensionType.OTHER  # for extensions that are not handled explicitly
                )

        def __init__(
            self,
            extension_type,  # type: str
            critical,  # type: bool
            oid=None,  # type: Optional[str]
            extension_name=None,  # type: Optional[str]
            subject_alternative_names=None,  # type: Optional[List[Common.CertificateExtension.SubjectAlternativeName]]
            authority_key_identifier=None,  # type: Optional[Common.CertificateExtension.AuthorityKeyIdentifier]
            digest=None,  # type: str
            digital_signature=None,  # type: Optional[bool]
            content_commitment=None,  # type: Optional[bool]
            key_encipherment=None,  # type: Optional[bool]
            data_encipherment=None,  # type: Optional[bool]
            key_agreement=None,  # type: Optional[bool]
            key_cert_sign=None,  # type: Optional[bool]
            crl_sign=None,  # type: Optional[bool]
            usages=None,  # type: Optional[List[str]]
            distribution_points=None,  # type: Optional[List[Common.CertificateExtension.DistributionPoint]]
            certificate_policies=None,  # type: Optional[List[Common.CertificateExtension.CertificatePolicy]]
            authority_information_access=None,  # type: Optional[List[Common.CertificateExtension.AuthorityInformationAccess]]
            basic_constraints=None,  # type: Optional[Common.CertificateExtension.BasicConstraints]
            signed_certificate_timestamps=None,  # type: Optional[List[Common.CertificateExtension.SignedCertificateTimestamp]]
            value=None  # type: Optional[Union[str, List[Any], Dict[str, Any]]]
        ):
            if not Common.CertificateExtension.ExtensionType.is_valid_type(extension_type):
                raise ConnectorError('algorithm must be of type Common.CertificateExtension.ExtensionType enum')

            self.extension_type = extension_type
            self.critical = critical

            if self.extension_type == Common.CertificateExtension.ExtensionType.SUBJECTALTERNATIVENAME:
                self.subject_alternative_names = subject_alternative_names
                self.oid = "2.5.29.17"
                self.extension_name = "subjectAltName"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.SUBJECTKEYIDENTIFIER:
                if not digest:
                    raise ConnectorError('digest is mandatory for SubjectKeyIdentifier extension')
                self.digest = digest
                self.oid = "2.5.29.14"
                self.extension_name = "subjectKeyIdentifier"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.KEYUSAGE:
                self.digital_signature = digital_signature
                self.content_commitment = content_commitment
                self.key_encipherment = key_encipherment
                self.data_encipherment = data_encipherment
                self.key_agreement = key_agreement
                self.key_cert_sign = key_cert_sign
                self.crl_sign = crl_sign
                self.oid = "2.5.29.15"
                self.extension_name = "keyUsage"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.EXTENDEDKEYUSAGE:
                if not usages:
                    raise ConnectorError('usages is mandatory for ExtendedKeyUsage extension')
                self.usages = usages
                self.oid = "2.5.29.37"
                self.extension_name = "extendedKeyUsage"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.AUTHORITYKEYIDENTIFIER:
                self.authority_key_identifier = authority_key_identifier
                self.oid = "2.5.29.35"
                self.extension_name = "authorityKeyIdentifier"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.CRLDISTRIBUTIONPOINTS:
                self.distribution_points = distribution_points
                self.oid = "2.5.29.31"
                self.extension_name = "cRLDistributionPoints"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.CERTIFICATEPOLICIES:
                self.certificate_policies = certificate_policies
                self.oid = "2.5.29.32"
                self.extension_name = "certificatePolicies"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.AUTHORITYINFORMATIONACCESS:
                self.authority_information_access = authority_information_access
                self.oid = "1.3.6.1.5.5.7.1.1"
                self.extension_name = "authorityInfoAccess"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.BASICCONSTRAINTS:
                self.basic_constraints = basic_constraints
                self.oid = "2.5.29.19"
                self.extension_name = "basicConstraints"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.PRESIGNEDCERTIFICATETIMESTAMPS:
                self.signed_certificate_timestamps = signed_certificate_timestamps
                self.oid = "1.3.6.1.4.1.11129.2.4.2"
                self.extension_name = "signedCertificateTimestampList"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.SIGNEDCERTIFICATETIMESTAMPS:
                self.signed_certificate_timestamps = signed_certificate_timestamps
                self.oid = "1.3.6.1.4.1.11129.2.4.5"
                self.extension_name = "signedCertificateTimestampList"

            elif self.extension_type == Common.CertificateExtension.ExtensionType.OTHER:
                self.value = value

            # override oid, extension_name if provided as inputs
            if oid:
                self.oid = oid
            if extension_name:
                self.extension_name = extension_name

        def to_context(self):
            extension_context = {
                "OID": self.oid,
                "Name": self.extension_name,
                "Critical": self.critical
            }  # type: Dict[str, Any]

            if (
                self.extension_type == Common.CertificateExtension.ExtensionType.SUBJECTALTERNATIVENAME
                and self.subject_alternative_names is not None
            ):
                extension_context["Value"] = [san.to_context() for san in self.subject_alternative_names]

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.AUTHORITYKEYIDENTIFIER
                and self.authority_key_identifier is not None
            ):
                extension_context["Value"] = self.authority_key_identifier.to_context()

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.SUBJECTKEYIDENTIFIER
                and self.digest is not None
            ):
                extension_context["Value"] = {
                    "Digest": self.digest
                }

            elif self.extension_type == Common.CertificateExtension.ExtensionType.KEYUSAGE:
                key_usage = {}  # type: Dict[str, bool]
                if self.digital_signature:
                    key_usage["DigitalSignature"] = self.digital_signature
                if self.content_commitment:
                    key_usage["ContentCommitment"] = self.content_commitment
                if self.key_encipherment:
                    key_usage["KeyEncipherment"] = self.key_encipherment
                if self.data_encipherment:
                    key_usage["DataEncipherment"] = self.data_encipherment
                if self.key_agreement:
                    key_usage["KeyAgreement"] = self.key_agreement
                if self.key_cert_sign:
                    key_usage["KeyCertSign"] = self.key_cert_sign
                if self.crl_sign:
                    key_usage["CrlSign"] = self.crl_sign

                if key_usage:
                    extension_context["Value"] = key_usage

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.EXTENDEDKEYUSAGE
                and self.usages is not None
            ):
                extension_context["Value"] = {
                    "Usages": [u for u in self.usages]
                }

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.CRLDISTRIBUTIONPOINTS
                and self.distribution_points is not None
            ):
                extension_context["Value"] = [dp.to_context() for dp in self.distribution_points]

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.CERTIFICATEPOLICIES
                and self.certificate_policies is not None
            ):
                extension_context["Value"] = [cp.to_context() for cp in self.certificate_policies]

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.AUTHORITYINFORMATIONACCESS
                and self.authority_information_access is not None
            ):
                extension_context["Value"] = [aia.to_context() for aia in self.authority_information_access]

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.BASICCONSTRAINTS
                and self.basic_constraints is not None
            ):
                extension_context["Value"] = self.basic_constraints.to_context()

            elif (
                self.extension_type in [
                    Common.CertificateExtension.ExtensionType.SIGNEDCERTIFICATETIMESTAMPS,
                    Common.CertificateExtension.ExtensionType.PRESIGNEDCERTIFICATETIMESTAMPS
                ]
                and self.signed_certificate_timestamps is not None
            ):
                extension_context["Value"] = [sct.to_context() for sct in self.signed_certificate_timestamps]

            elif (
                self.extension_type == Common.CertificateExtension.ExtensionType.OTHER
                and self.value is not None
            ):
                extension_context["Value"] = self.value

            return extension_context

    class Certificate(Indicator):
        """
        Implements the X509 Certificate interface
        Certificate indicator - https://xsoar.pan.dev/docs/integrations/context-standards-mandatory#certificate

        :type subject_dn: ``str``
        :param subject_dn: Subject Distinguished Name

        :type dbot_score: ``DBotScore``
        :param dbot_score: If Certificate has a score then create and set a DBotScore object.

        :type name: ``Optional[Union[str, List[str]]]``
        :param name: Name (if not provided output is calculated from SubjectDN and SAN)

        :type issuer_dn: ``Optional[str]``
        :param issuer_dn: Issuer Distinguished Name

        :type serial_number: ``Optional[str]``
        :param serial_number: Serial Number

        :type validity_not_after: ``Optional[str]``
        :param validity_not_after: Certificate Expiration Timestamp (ISO8601 string representation)

        :type validity_not_before: ``Optional[str]``
        :param validity_not_before: Initial Certificate Validity Timestamp (ISO8601 string representation)

        :type sha512: ``Optional[str]``
        :param sha512: The SHA-512 hash of the certificate in binary encoded format (DER)

        :type sha256: ``Optional[str]``
        :param sha256: The SHA-256 hash of the certificate in binary encoded format (DER)

        :type sha1: ``Optional[str]``
        :param sha1: The SHA-1 hash of the certificate in binary encoded format (DER)

        :type md5: ``Optional[str]``
        :param md5: The MD5 hash of the certificate in binary encoded format (DER)

        :type publickey: ``Optional[Common.CertificatePublicKey]``
        :param publickey: Certificate Public Key

        :type spki_sha256: ``Optional[str]``
        :param sha1: The SHA-256 hash of the SPKI

        :type signature_algorithm: ``Optional[str]``
        :param signature_algorithm: Signature Algorithm

        :type signature: ``Optional[str]``
        :param signature: Certificate Signature

        :type subject_alternative_name: \
        ``Optional[List[Union[str,Dict[str, str],Common.CertificateExtension.SubjectAlternativeName]]]``
        :param subject_alternative_name: Subject Alternative Name list

        :type extensions: ``Optional[List[Common.CertificateExtension]]`
        :param extensions: Certificate Extension List

        :type pem: ``Optional[str]``
        :param pem: PEM encoded certificate

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'Certificate(val.MD5 && val.MD5 == obj.MD5 || val.SHA1 && val.SHA1 == obj.SHA1 || ' \
                        'val.SHA256 && val.SHA256 == obj.SHA256 || val.SHA512 && val.SHA512 == obj.SHA512)'

        def __init__(
            self,
            subject_dn,  # type: str
            dbot_score=None,  # type: Optional[Common.DBotScore]
            name=None,  # type: Optional[Union[str, List[str]]]
            issuer_dn=None,  # type: Optional[str]
            serial_number=None,  # type: Optional[str]
            validity_not_after=None,  # type: Optional[str]
            validity_not_before=None,  # type: Optional[str]
            sha512=None,  # type: Optional[str]
            sha256=None,  # type: Optional[str]
            sha1=None,  # type: Optional[str]
            md5=None,  # type: Optional[str]
            publickey=None,  # type: Optional[Common.CertificatePublicKey]
            spki_sha256=None,  # type: Optional[str]
            signature_algorithm=None,  # type: Optional[str]
            signature=None,  # type: Optional[str]
            subject_alternative_name=None, \
            # type: Optional[List[Union[str,Dict[str, str],Common.CertificateExtension.SubjectAlternativeName]]]
            extensions=None,  # type: Optional[List[Common.CertificateExtension]]
            pem=None  # type: Optional[str]

        ):

            self.subject_dn = subject_dn
            self.dbot_score = dbot_score

            self.name = None
            if name:
                if isinstance(name, str):
                    self.name = [name]
                elif isinstance(name, list):
                    self.name = name
                else:
                    raise ConnectorError('certificate name must be of type str or List[str]')

            self.issuer_dn = issuer_dn
            self.serial_number = serial_number
            self.validity_not_after = validity_not_after
            self.validity_not_before = validity_not_before

            self.sha512 = sha512
            self.sha256 = sha256
            self.sha1 = sha1
            self.md5 = md5

            if publickey and not isinstance(publickey, Common.CertificatePublicKey):
                raise ConnectorError('publickey must be of type Common.CertificatePublicKey')
            self.publickey = publickey

            self.spki_sha256 = spki_sha256

            self.signature_algorithm = signature_algorithm
            self.signature = signature

            # if subject_alternative_name is set and is a list
            # make sure it is a list of strings, dicts of strings or SAN Extensions
            if (
                subject_alternative_name
                and isinstance(subject_alternative_name, list)
                and not all(
                    isinstance(san, str)
                    or isinstance(san, dict)
                    or isinstance(san, Common.CertificateExtension.SubjectAlternativeName)
                    for san in subject_alternative_name)
            ):
                raise ConnectorError(
                    'subject_alternative_name must be list of str or Common.CertificateExtension.SubjectAlternativeName'
                )
            self.subject_alternative_name = subject_alternative_name

            if (
                extensions
                and not isinstance(extensions, list)
                and any(isinstance(e, Common.CertificateExtension) for e in extensions)  # type: ignore
            ):
                raise ConnectorError('extensions must be of type List[Common.CertificateExtension]')
            self.extensions = extensions

            self.pem = pem

            if not isinstance(dbot_score, Common.DBotScore):
                raise ConnectorError('dbot_score must be of type DBotScore')

        def to_context(self):
            certificate_context = {
                "SubjectDN": self.subject_dn
            }  # type: Dict[str, Any]

            san_list = []  # type: List[Dict[str, str]]
            if self.subject_alternative_name:
                for san in self.subject_alternative_name:
                    if isinstance(san, str):
                        san_list.append({
                            'Value': san
                        })
                    elif isinstance(san, dict):
                        san_list.append(san)
                    elif (isinstance(san, Common.CertificateExtension.SubjectAlternativeName)):
                        san_list.append(san.to_context())

            elif self.extensions:  # autogenerate it from extensions
                for ext in self.extensions:
                    if (
                        ext.extension_type == Common.CertificateExtension.ExtensionType.SUBJECTALTERNATIVENAME
                        and ext.subject_alternative_names is not None
                    ):
                        for san in ext.subject_alternative_names:
                            san_list.append(san.to_context())

            if san_list:
                certificate_context['SubjectAlternativeName'] = san_list

            if self.name:
                certificate_context["Name"] = self.name
            else:  # autogenerate it
                name = set()  # type: Set[str]
                # add subject alternative names
                if san_list:
                    name = set([
                        sn['Value'] for sn in san_list
                        if (
                            'Value' in sn
                            and (
                                'Type' not in sn
                                or sn['Type'] in (Common.GeneralName.DNSNAME, Common.GeneralName.IPADDRESS)
                            )
                        )
                    ])

                # subject_dn is RFC4515 escaped
                # replace \, and \+ with the long escaping \2c and \2b
                long_escaped_subject_dn = self.subject_dn.replace("\\,", "\\2c")
                long_escaped_subject_dn = long_escaped_subject_dn.replace("\\+", "\\2b")
                # we then split RDN (separated by ,) and multi-valued RDN (sep by +)
                rdns = long_escaped_subject_dn.replace('+', ',').split(',')
                cn = next((rdn for rdn in rdns if rdn.startswith('CN=')), None)
                if cn:
                    name.add(cn.split('=', 1)[-1])

                if name:
                    certificate_context["Name"] = sorted(list(name))

            if self.issuer_dn:
                certificate_context["IssuerDN"] = self.issuer_dn

            if self.serial_number:
                certificate_context["SerialNumber"] = self.serial_number

            if self.validity_not_before:
                certificate_context["ValidityNotBefore"] = self.validity_not_before

            if self.validity_not_after:
                certificate_context["ValidityNotAfter"] = self.validity_not_after

            if self.sha512:
                certificate_context["SHA512"] = self.sha512

            if self.sha256:
                certificate_context["SHA256"] = self.sha256

            if self.sha1:
                certificate_context["SHA1"] = self.sha1

            if self.md5:
                certificate_context["MD5"] = self.md5

            if self.publickey and isinstance(self.publickey, Common.CertificatePublicKey):
                certificate_context["PublicKey"] = self.publickey.to_context()

            if self.spki_sha256:
                certificate_context["SPKISHA256"] = self.spki_sha256

            sig = {}  # type: Dict[str, str]
            if self.signature_algorithm:
                sig["Algorithm"] = self.signature_algorithm
            if self.signature:
                sig["Signature"] = self.signature
            if sig:
                certificate_context["Signature"] = sig

            if self.extensions:
                certificate_context["Extension"] = [e.to_context() for e in self.extensions]

            if self.pem:
                certificate_context["PEM"] = self.pem

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                certificate_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            ret_value = {
                Common.Certificate.CONTEXT_PATH: certificate_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value

    class Tactic(Indicator):
        """
        Tactic indicator

        :type stix_id: ``str``
        :param stix_id: The Tactic STIX ID

        :type first_seen_by_source: ``str``
        :param first_seen_by_source: The Tactic first seen by source

        :type description: ``str``
        :param description: The Tactic description

        :type publications: ``str``
        :param publications: The Tactic publications

        :type mitre_id: ``str``
        :param mitre_id: The Tactic mitre id.

        :type tags: ``str``
        :param tags: The Tactic tags.

        :type dbot_score: ``DBotScore``
        :param dbot_score:  If the address has reputation then create DBotScore object.

        :type traffic_light_protocol: ``str``
        :param traffic_light_protocol: The Traffic Light Protocol (TLP) color that is suitable for the Tactic.

        :type community_notes: ``CommunityNotes``
        :param community_notes:  A list of community notes for the Tactic.

        :type external_references: ``ExternalReference``
        :param external_references:  A list of id's and description of the Tactic via external refs.

        :type value: ``str``
        :param value: The Tactic value (name) - example: "Plist File Modification"

        :return: None
        :rtype: ``None``
        """
        CONTEXT_PATH = 'Tactic(val.Name && val.Name == obj.Name)'

        def __init__(self, stix_id, first_seen_by_source=None, description=None, publications=None, mitre_id=None, tags=None,
                    traffic_light_protocol=None, dbot_score=None, community_notes=None, external_references=None, value=None):

            self.community_notes = community_notes
            self.description = description
            self.external_references = external_references
            self.first_seen_by_source = first_seen_by_source
            self.mitre_id = mitre_id
            self.publications = publications
            self.stix_id = stix_id
            self.tags = tags
            self.traffic_light_protocol = traffic_light_protocol
            self.value = value
            self.dbot_score = dbot_score

        def to_context(self):
            attack_pattern_context = {
                'STIXID': self.stix_id,
                "FirstSeenBySource": self.first_seen_by_source,
                "Publications": self.publications,
                "MITREID": self.mitre_id,
                "Value": self.value,
                "Tags": self.tags,
                "Description": self.description
            }

            if self.external_references:
                attack_pattern_context['ExternalReferences'] = self.create_context_table(self.external_references)

            if self.traffic_light_protocol:
                attack_pattern_context['TrafficLightProtocol'] = self.traffic_light_protocol

            if self.dbot_score and self.dbot_score.score == Common.DBotScore.BAD:
                attack_pattern_context['Malicious'] = {
                    'Vendor': self.dbot_score.integration_name,
                    'Description': self.dbot_score.malicious_description
                }

            ret_value = {
                Common.AttackPattern.CONTEXT_PATH: attack_pattern_context
            }

            if self.dbot_score:
                ret_value.update(self.dbot_score.to_context())

            return ret_value