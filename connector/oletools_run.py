from connectors.core.connector import get_logger, ConnectorError
from .utils import *
from connectors.cyops_utilities.builtins import download_file_from_cyops
from .constants import LOGGER_NAME
import os
import subprocess
import hashlib

logger = get_logger(LOGGER_NAME)

# should be imported after adding log handler to the root logger
# consts
TMP_PATH = '/tmp/'

from oletools import crypto, oleid  # noqa: E402
#from oletools.oleobj import find_external_links
from oletools.olevba import VBA_Parser  # noqa: E402

def oletools_run(config, params):
    #args = params
    ole_command = params.get("oleCommand")
    # attach_id = args.get("entryID", "")
    # file_info = demisto.getFilePath(attach_id)
    show_decoded = params.get("decode", False)
    password = params.get("password", "")
    non_secret_password = params.get("non_secret_password", "")
    file_path = ''
    file_name = ''
    
    if params.get('entryID') and '/api/3/files/' not in params.get('entryID'):
        file_path = os.path.join(TMP_PATH, params.get('entryID'))
        file_name = os.path.basename(params.get('entryID'))
    else:
        file_iri = params.get('entryID')
        dw_file_md = download_file_from_cyops(file_iri)
        file_path = TMP_PATH + dw_file_md['cyops_file_path']
        file_name = dw_file_md['filename']
    file_info = {
        "name":file_name,
        "path":file_path
    }
    try:
        password = handle_password(password=password, non_secret_password=non_secret_password)
        ole_client = OleClient(file_info, ole_command, password=password, decoded=show_decoded)
        result = ole_client.run().to_context()
        return result
    except Exception as e:
        logger.exception(e)
        raise ConnectorError(
            f"The script failed with the following error:\n {e}"
        )
    

class OleClient:
    def __init__(self, file_info, ole_command, password=None, decoded=False):
        self.name = file_info["name"]
        self.file_path = file_info["path"]
        self.password = password
        self.show_decoded = decoded
        self.decrypted_file_path = None
        self.processed_file_path = file_info["path"]
        self.ole_command = ole_command
        self.hash = None

    def __del__(self):
        try:
            if self.password and self.decrypted_file_path:
                os.unlink(self.decrypted_file_path)
        except Exception:  # e.g. file does not exist or is None
            pass

    def decryption(self):
        if crypto.is_encrypted(self.file_path) and self.password:
            try:
                passwords = [self.password] + crypto.DEFAULT_PASSWORDS
                self.decrypted_file_path = crypto.decrypt(self.file_path, passwords)
                if not self.decrypted_file_path:
                    raise crypto.WrongEncryptionPassword(self.file_path)
            except Exception as e:
                raise ConnectorError(f"The file decryption failed with the following message:\n {e}")

    @staticmethod
    def calc_hash(file_path: str):
        with open(file_path, "rb") as f:
            b = f.read()  # read entire file as bytes
            return hashlib.sha256(b).hexdigest()

    def run(self):
        self.decryption()

        if self.decrypted_file_path:
            self.processed_file_path = self.decrypted_file_path

        # calculate the file hash
        self.hash = self.calc_hash(self.processed_file_path)

        if self.ole_command == "oleid":
            cr = self.oleid()
        elif self.ole_command == "oleobj":
            cr = self.oleobj()
        elif self.ole_command == "olevba":
            cr = self.olevba()
        else:
            raise NotImplementedError(f'Command "{self.ole_command}" is not implemented.')

        self.wrap_command_result(cr)
        return cr

    def wrap_command_result(self, cr: CommandResults):
        cr.outputs = {"sha256": self.hash, "file_name": self.name, "ole_command_result": cr.outputs}
        cr.outputs_key_field = "sha256"

    @staticmethod
    def replace_space_with_underscore(indicator: str):
        return indicator.replace(" ", "_")

    def oleid(self):
        oid = oleid.OleID(self.processed_file_path)
        indicators = oid.check()
        indicators_list = []
        dbot_score = None
        indicators_dict = {}
        for i in indicators:
            indicators_list.append(
                {"Indicator": str(i.name), "Value": str(i.value), "Ole Risk": str(i.risk), "Description": str(i.description)}
            )

            if str(i.name):
                indicators_dict[self.replace_space_with_underscore(str(i.name))] = {
                    "Value": str(i.value),
                    "Ole_Risk": str(i.risk),
                    "Description": str(i.description),
                }

            if str(i.name) == "VBA Macros" and str(i.risk) == "HIGH":
                dbot_score = Common.DBotScore(self.hash, DBotScoreType.FILE, "Oletools", Common.DBotScore.BAD)

        indicator = Common.File(dbot_score, sha256=self.hash) if dbot_score else None
        cr = CommandResults(
            readable_output=tableToMarkdown(self.name, indicators_list, headers=["Indicator", "Value", "Ole Risk", "Description"])
            + f"\n file hash: {self.hash}",
            outputs=indicators_dict,
            outputs_prefix="Oletools.Oleid",
            indicator=indicator,
        )
        return cr

    def oleobj(self):
        """完全兼容 oletools 0.60.2 的实现"""
        try:
            # 方法1：使用 OleObject 的正确打开方式
            from oletools.oleobj import OleObject
            
            # 使用临时文件捕获输出
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
                tmp_path = tmp.name
            
            # 必须以二进制模式打开文件
            with open(self.processed_file_path, 'rb') as f:
                file_data = f.read()
            
            # 处理文件
            parser = OleObject(self.processed_file_path)
            with open(tmp_path, 'w') as f:
                import sys
                old_stdout = sys.stdout
                sys.stdout = f
                parser.process_file()
                sys.stdout = old_stdout
            
            # 读取输出
            with open(tmp_path, 'r') as f:
                output = f.read()
            
            # 清理临时文件
            import os
            os.unlink(tmp_path)
            
            # 解析输出
            hyperlinks = []
            for line in output.splitlines():
                if "external link" in line and "http" in line:
                    # 提取形如: Found relationship 'hyperlink' with external link 'http://example.com'
                    parts = line.split("'")
                    if len(parts) >= 4:
                        hyperlinks.append(parts[3])
            
            return CommandResults(
                readable_output="### Found external links:\n" + "\n".join(f"- {link}" for link in hyperlinks),
                outputs_prefix="Oletools.Oleobj",
                outputs={"hyperlinks": hyperlinks},
                raw_response=output
            )
            
        except Exception as e:
            # 方法2：纯Python应急实现
            try:
                return self._pure_python_fallback()
            except Exception as fallback_error:
                raise ConnectorError(
                    f"Failed to process oleobj: {str(e)}\n"
                    f"Fallback also failed: {str(fallback_error)}\n"
                    f"Please ensure file is valid OLE document: {self.processed_file_path}"
                )

    def _pure_python_fallback(self):
        """纯Python实现的应急方案"""
        with open(self.processed_file_path, 'rb') as f:
            data = f.read()
        
        # 简单搜索URL模式
        import re
        urls = re.findall(b'https?://[^\s\x00-\x1f\x7f-\xff]+', data)
        hyperlinks = [url.decode('latin1', errors='ignore') for url in urls]
        
        return CommandResults(
            readable_output="### Found possible links:\n" + "\n".join(f"- {link}" for link in hyperlinks),
            outputs_prefix="Oletools.Oleobj",
            outputs={"hyperlinks": hyperlinks},
            raw_response=str(hyperlinks)
        )

    def olevba(self):
        file_data = open(self.processed_file_path, "rb").read()
        vbaparser = VBA_Parser(self.processed_file_path, data=file_data, disable_pcode=True)

        if not vbaparser.detect_vba_macros():
            return CommandResults(readable_output="### No VBA Macros found\n")

        found = "### VBA Macros found\n"
        all_macros = vbaparser.extract_all_macros()
        macros_list = []

        for macro in all_macros:
            macros_list.append({"VBA Macro": macro[2], "Found in file": macro[0], "Ole stream": macro[1]})

        macros_list_md = tableToMarkdown("Macros found", macros_list, headers=["VBA Macro", "Found in file", "Ole stream"])

        macro_source_code = vbaparser.reveal()
        readable_macro = f"\n### Macro source code\n {macro_source_code}\n"

        results = vbaparser.analyze_macros(show_decoded_strings=self.show_decoded)
        results_list = []
        for result in results:
            results_list.append({"Type": result[0], "Keyword": result[1], "Description": result[2]})

        results_md = tableToMarkdown("Macro Analyze", results_list, headers=["Type", "Keyword", "Description"])
        vbaparser.close()

        readable_output = found + macros_list_md + readable_macro + results_md
        outputs = {"macro_list": macros_list, "macro_src_code": macro_source_code, "macro_analyze": results_list}
        cr = CommandResults(readable_output=readable_output, outputs_prefix="Oletools.Olevba", outputs=outputs)
        return cr


def handle_password(non_secret_password: str, password: str) -> str:
    if non_secret_password and not password:
        return non_secret_password
    elif password and non_secret_password:
        raise ValueError("Please insert a password or a non_secret_password not both")
    return password