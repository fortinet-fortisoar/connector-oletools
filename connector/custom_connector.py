import os
import hashlib
import subprocess
import re
from datetime import datetime, date
import decimal
from typing import Literal, Optional, Union, Any
from connectors.cyops_utilities.builtins import download_file_from_cyops

from oletools import crypto, oleid, oleobj
from oletools.olevba import VBA_Parser


class CustomConnector:
    def __init__(self):
        pass

    def _make_jsonable(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._make_jsonable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_jsonable(v) for v in obj]
        elif isinstance(obj, set):
            return [self._make_jsonable(v) for v in obj]
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, (bytes, bytearray)):
            return obj.decode("utf-8", errors="replace")
        else:
            return str(obj)

    def _decrypt_file(self, file_path: str, file_password: Optional[str] = "") -> Optional[str]:
        if crypto.is_encrypted(file_path) and file_password:
            try:
                passwords = [file_password] + crypto.DEFAULT_PASSWORDS
                self.decrypted_file_path = crypto.decrypt(file_path, passwords)
                if not self.decrypted_file_path:
                    raise crypto.WrongEncryptionPassword(file_path)
            except Exception as e:
                raise Exception(f"File decrypt failed: {e}")

    def _prepare_file(self, file_iri: str, file_password: Optional[str] = "") -> tuple:
        """Prepare file for processing

        Returns:
            str: file_path
            str: file_name
        """
        if file_iri.startswith("/api/3/files/"):
            cyops_file = download_file_from_cyops(file_iri)
            file_path = os.path.join("/tmp", cyops_file["cyops_file_path"])
            file_name = cyops_file["filename"]
        else:
            file_path = os.path.join("/tmp", file_iri)
            file_name = os.path.basename(file_iri)

        file_hash_sha256_hex = ""
        file_hash_md5_hex = ""

        with open(file_path, "rb") as f:
            file_data = f.read()

            sha256_hash = hashlib.sha256()
            sha256_hash.update(file_data)
            file_hash_sha256_hex = sha256_hash.hexdigest()

            md5_hash = hashlib.md5()
            md5_hash.update(file_data)
            file_hash_md5_hex = md5_hash.hexdigest()
        # calculate hashs

        decrypted_file_path = self._decrypt_file(file_path, file_password) if file_password else None
        if decrypted_file_path:
            file_path = decrypted_file_path

        return (file_path, file_name, {"sha256": file_hash_sha256_hex, "md5": file_hash_md5_hex})

    def oleid(self, file_iri: str, file_password: Optional[str] = "") -> dict:
        """oleid
        - API Doc: <https://github.com/decalage2/oletools/wiki/oleid>
        """
        file_path, file_name, file_hash = self._prepare_file(file_iri, file_password)

        retval = {"indicators": [], "hash": file_hash}

        oid = oleid.OleID(file_path)
        indicators = oid.check()
        for _ind in indicators:
            retval["indicators"].append(
                {
                    "id": _ind.id,
                    "description": _ind.description,
                    "name": _ind.name,
                    "type": _ind.type,
                    "value": _ind.value,
                    "risk": _ind.risk,
                }
            )

        return self._make_jsonable(retval)

    def oleobj(self, file_iri: str, file_password: Optional[str] = "") -> dict:
        """_summary_
        - API Doc: <https://github.com/decalage2/oletools/wiki/oleid>"""
        file_path, file_name, file_hash = self._prepare_file(file_iri, file_password)
        retval = {"hyperlinks": [], "stdout": ""}

        stdout = subprocess.run(
            [
                "sudo",
                "-u",
                "fsr-integrations",
                "/opt/cyops-integrations/.env/bin/python3",
                "-m",
                "oletools.oleobj",
                "-i",
                file_path,
            ],
            capture_output=True,
        )
        regex = r"Found relationship 'hyperlink' with external link (.*?)\n"
        retval["stdout"] = stdout.stdout.decode("utf-8")
        matches = re.findall(regex, retval["stdout"], re.MULTILINE)
        for match in matches:
            retval["hyperlinks"].append(match)

        return self._make_jsonable(retval)

    def olevba(
        self,
        file_iri: str,
        file_password: Optional[str] = "",
        show_decoded_strings: bool = False,
        deobfuscate: bool = False,
    ) -> dict:
        """olevba is a script to parse OLE and OpenXML files such as MS Office documents.
        - API Doc: <https://github.com/decalage2/oletools/wiki/olevba>"""
        file_path, file_name, file_hash = self._prepare_file(file_iri, file_password)
        retval = {}

        with open(file_path, "rb") as f:
            file_data = f.read()

            vbaparser = VBA_Parser(file_path, data=file_data)
            retval["detect_vba_macros"] = vbaparser.detect_vba_macros()

            retval["extract_macros"] = []
            for filename, stream_path, vba_filename, vba_code in vbaparser.extract_macros():
                retval["extract_macros"].append(
                    {
                        "file_name": filename,
                        "stream_path": stream_path,
                        "vba_filename": vba_filename,
                        "vba_code": vba_code,
                    }
                )

            results = vbaparser.analyze_macros(show_decoded_strings=show_decoded_strings, deobfuscate=deobfuscate)
            if results:
                retval["analyze_macros"] = []
                for kw_type, keyword, description in results:
                    retval["analyze_macros"].append({"type": kw_type, "keyword": keyword, "description": description})

                retval["nb_autoexec"] = vbaparser.nb_autoexec
                retval["nb_suspicious"] = vbaparser.nb_suspicious
                retval["nb_iocs"] = vbaparser.nb_iocs
                retval["nb_hexstrings"] = vbaparser.nb_hexstrings
                retval["nb_base64strings"] = vbaparser.nb_base64strings
                retval["nb_dridexstrings"] = vbaparser.nb_dridexstrings
                retval["nb_vbastrings"] = vbaparser.nb_vbastrings

                retval["reveal"] = vbaparser.reveal()
            else:
                pass

            vbaparser.close()

        return self._make_jsonable(retval)
