"""VESTE local worker. Run inside your existing FASHN virtualenv.
Uses only the signed-in user's Supabase permissions. No public listener.
"""
import getpass
import io
import json
import pathlib
import time
import uuid
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote
from urllib.error import HTTPError, URLError

from PIL import Image, ImageOps
import torch
from fashn_vton import TryOnPipeline

URL = "https://zodyzmeeossstkiwanqi.supabase.co"
PUBLIC_KEY = "sb_publishable_26b9DoYuHezMJ06urxRk9w_qCE_TtlU"
BUCKET = "veste-try-private"
TABLE = "/rest/v1/veste_try_jobs"
CATEGORIES = {"tops", "bottoms", "one-pieces"}
MAX_BYTES = 8 * 1024 * 1024

def now():
    return datetime.now(timezone.utc).isoformat()

class APIError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)

class API:
    def __init__(self,email,password):
        self.token = None
        self.refresh = None
        self.expiry = 0
        self.uid = None
        self.login(email,password)

    def request(self,method,path,body=None,query=None,raw=False,auth=True,headers=None):
        if auth and time.time() >= self.expiry - 90:
            self.renew()
        h = {"apikey":PUBLIC_KEY}
        if auth:
            h["Authorization"] = "Bearer "+self.token
        if headers:
            h.update(headers)
        if isinstance(body,(dict,list)):
            body = json.dumps(body).encode("utf-8")
            h["Content-Type"] = "application/json"
        address = URL + path + ("?"+urlencode(query) if query else "")
        try:
            with urlopen(Request(address,data=body,headers=h,method=method),timeout=60) as response:
                data=response.read(MAX_BYTES+1 if raw else 2*1024*1024)
                if raw:
                    if len(data)>MAX_BYTES:
                        raise ValueError("Foto acima do limite.")
                    return data
                return json.loads(data) if data else None
        except HTTPError as exc:
            raise APIError(exc.code,"Supabase HTTP "+str(exc.code)) from None

    def _session(self,result):
        self.token=result["access_token"]
        self.refresh=result["refresh_token"]
        self.expiry=time.time()+int(result.get("expires_in",3600))
        uid=str(uuid.UUID(result["user"]["id"]))
        if self.uid and self.uid!=uid:
            raise ValueError("Conta alterada.")
        self.uid=uid

    def login(self,email,password):
        self._session(self.request("POST","/auth/v1/token",{"email":email,"password":password},{"grant_type":"password"},auth=False))

    def renew(self):
        self._session(self.request("POST","/auth/v1/token",{"refresh_token":self.refresh},{"grant_type":"refresh_token"},auth=False))

    def rows(self,**query):
        return self.request("GET",TABLE,query={"user_id":"eq."+self.uid,**query})

    def patch(self,jobid,expected,**changes):
        return self.request("PATCH",TABLE,{"updated_at":now(),**changes},{"user_id":"eq."+self.uid,"id":"eq."+jobid,"status":"eq."+expected},headers={"Prefer":"return=representation"})

    def get_photo(self,path):
        return self.request("GET","/storage/v1/object/authenticated/"+BUCKET+"/"+quote(path,safe="/"),raw=True)

    def put_photo(self,path,data):
        return self.request("POST","/storage/v1/object/"+BUCKET+"/"+quote(path,safe="/"),data,headers={"Content-Type":"image/jpeg","x-upsert":"false"})

    def remove(self,paths):
        return self.request("DELETE","/storage/v1/object/"+BUCKET,{"prefixes":paths})

def decode_photo(data):
    with Image.open(io.BytesIO(data)) as picture:
        if picture.width*picture.height>16000000:
            raise ValueError("Foto grande demais.")
        return ImageOps.exif_transpose(picture).convert("RGB")

def process(api,pipeline,job):
    jid=str(uuid.UUID(job["id"]))
    assert job["user_id"]==api.uid
    categories=job["categories"]
    if not isinstance(categories,list) or not 1<=len(categories)<=3 or any(c not in CATEGORIES for c in categories):
        raise ValueError("Categorias inválidas.")
    prefix=api.uid+"/"+jid+"/"
    inputs=[prefix+"person.jpg"]+[prefix+"garment"+str(i)+".jpg" for i in range(len(categories))]
    if not api.patch(jid,"queued",status="running",progress=0,error_message=None):
        return
    print("Pedido recebido:",jid,flush=True)
    finished=False
    try:
        person=decode_photo(api.get_photo(inputs[0]))
        for i,category in enumerate(categories):
            garment=decode_photo(api.get_photo(inputs[i+1]))
            print("Etapa",i+1,"/",len(categories),category,flush=True)
            result=pipeline(person_image=person,garment_image=garment,category=category,garment_photo_type="flat-lay",num_samples=1,num_timesteps=30)
            person=result.images[0].convert("RGB")
            del result,garment
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            api.patch(jid,"running",progress=i+1)
        output=io.BytesIO()
        person.save(output,format="JPEG",quality=92)
        api.put_photo(prefix+"result.jpg",output.getvalue())
        finished=bool(api.patch(jid,"running",status="done",progress=len(categories)))
        print("Simulação pronta.",flush=True)
    except Exception as exc:
        print("Falha na geração:",type(exc).__name__,str(exc)[:250],flush=True)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        try:
            if api.patch(jid,"running",status="error",error_message="Falha no processamento. Verifique o PowerShell, as fotos e a memória da GPU."):
                finished=True
        except Exception:
            pass
    finally:
        if finished:
            try:
                api.remove(inputs)
            except Exception:
                print("Não consegui limpar as fotos temporárias; exclua o pedido no VESTE.",flush=True)

def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA indisponível. Abra o ambiente Python que funcionou no teste.")
    weights=pathlib.Path(__file__).resolve().parent/"weights"
    if not weights.is_dir():
        raise SystemExit("Coloque este arquivo dentro da pasta fashn-vton-1.5.")
    print("VESTE — provador privado no PC")
    print("Entre com o MESMO e-mail e senha utilizados no aplicativo VESTE.")
    email=input("E-mail VESTE: ").strip()
    password=getpass.getpass("Senha VESTE (não aparece ao digitar): ")
    try:
        api=API(email,password)
    except APIError as exc:
        raise SystemExit("Falha no login. Confira os dados e se o e-mail foi confirmado. "+str(exc))
    finally:
        del password
    print("GPU:",torch.cuda.get_device_name(0),flush=True)
    print("Carregando FASHN...",flush=True)
    pipeline=TryOnPipeline(weights_dir=str(weights),device="cuda")
    print("VESTE CONECTADO — aguardando pedidos. Ctrl+C para encerrar.",flush=True)
    while True:
        try:
            cutoff=(datetime.now(timezone.utc)-timedelta(minutes=30)).isoformat()
            for stale in api.rows(select="id",status="eq.running",updated_at="lt."+cutoff):
                api.patch(str(uuid.UUID(stale["id"])),"running",status="error",error_message="Pedido interrompido. Exclua e envie novamente.")
            jobs=api.rows(select="id,user_id,categories,status",status="eq.queued",order="created_at.asc",limit="1")
            if jobs:
                process(api,pipeline,jobs[0])
            else:
                time.sleep(12)
        except APIError as exc:
            if exc.status in (401,403):
                raise SystemExit("Sessão expirada. Reinicie o programa e entre novamente.")
            print("Erro de conexão:",str(exc),flush=True)
            time.sleep(20)
        except (URLError,TimeoutError) as exc:
            print("Sem conexão. Nova tentativa em 20 segundos.",flush=True)
            time.sleep(20)

if __name__=="__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nVESTE encerrado.")
