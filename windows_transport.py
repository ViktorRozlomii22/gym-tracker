"""PTB transport via Windows HTTPS, retaining system certificate validation.

Optional compatibility path for environments where Python TLS initialization fails.
Secrets travel over stdin, never command-line arguments or log messages.
"""
import asyncio
import base64
import json
from pathlib import Path
import secrets
import subprocess
from telegram.request import BaseRequest
from telegram.error import NetworkError

class WindowsRequest(BaseRequest):
    @property
    def read_timeout(self):
        return 50

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self,url,method,request_data=None,**kwargs):
        fields = request_data.json_parameters if request_data else {}
        files = request_data.multipart_data if request_data else {}
        if files:
            boundary = 'NextSet' + secrets.token_hex(16)
            chunks=[]
            for key,value in fields.items():
                chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
            for key,(filename,blob,mime) in files.items():
                if hasattr(blob,'read'):
                    blob=blob.read()
                filename = filename.replace('"','').replace('\r','').replace('\n','')
                chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode()+blob+b'\r\n')
            chunks.append(f'--{boundary}--\r\n'.encode())
            body,content_type=b''.join(chunks),f'multipart/form-data; boundary={boundary}'
        else:
            body,content_type=json.dumps(fields).encode(),'application/json'
        payload=json.dumps({'url':url,'body':base64.b64encode(body).decode(),'content_type':content_type})
        def request():
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(Path(__file__).with_name('windows_http.ps1'))],input=payload,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:
                raise NetworkError('Windows HTTPS unavailable')
            try:
                data=json.loads(result.stdout)
                return data['status'],base64.b64decode(data['body'])
            except (KeyError,ValueError):
                raise NetworkError('Invalid Windows HTTPS response') from None
        try:
            return await asyncio.to_thread(request)
        except (OSError,subprocess.TimeoutExpired):
            raise NetworkError('Windows HTTPS unavailable') from None
