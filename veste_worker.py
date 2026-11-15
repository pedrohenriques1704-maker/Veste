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
            print("Etapa",i+1,"/",len(categories),category,"— modo", "original" if i==0 else "com máscara (experimental)",flush=True)
            result=pipeline(person_image=person,garment_image=garment,category=category,garment_photo_type="flat-lay",num_samples=1,num_timesteps=30,segmentation_free=(i==0))
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
    print("VESTE 4.9 — provador privado no PC (multicontas)")
    print("Cada pessoa deve autorizar sua própria conta VESTE.")
    print("As senhas não serão gravadas. Uma GPU, um pedido por vez.")
    accounts = []
    while True:
        choice = input("Quantas contas deseja conectar? [1/2]: ").strip() or "2"
        if choice in ("1", "2"):
            break
        print("Escolha 1 ou 2.")
    for index in range(int(choice)):
        while True:
            email = input("E-mail VESTE da conta "+str(index+1)+": ").strip()
            password = getpass.getpass("Senha VESTE (não aparece ao digitar): ")
            try:
                api = API(email, password)
                if any(a.uid == api.uid for a in accounts):
                    print("Esta conta já foi conectada. Use a outra conta.")
                    continue
                accounts.append(api)
                print("Conta "+str(index+1)+" conectada.", flush=True)
                break
            except (APIError, URLError, TimeoutError):
                print("Não foi possível autenticar. Confira os dados ou a conexão e tente novamente.")
            finally:
                del password
    print("GPU:",torch.cuda.get_device_name(0),flush=True)
    print("Carregando FASHN...",flush=True)
    pipeline=TryOnPipeline(weights_dir=str(weights),device="cuda")
    print("VESTE CONECTADO — "+str(len(accounts))+" conta(s), aguardando pedidos. Ctrl+C para encerrar.",flush=True)
    # Each account retains its own authenticated API client and refresh token.
    # Never use a privileged key or substitute the identity of another account.
    while accounts:
        candidates = []
        unavailable = []
        for index, api in enumerate(accounts):
            try:
                cutoff=(datetime.now(timezone.utc)-timedelta(minutes=30)).isoformat()
                for stale in api.rows(select="id",status="eq.running",updated_at="lt."+cutoff):
                    api.patch(str(uuid.UUID(stale["id"])),"running",status="error",error_message="Pedido interrompido. Exclua e envie novamente.")
                jobs=api.rows(select="id,user_id,categories,status,created_at",status="eq.queued",order="created_at.asc",limit="1")
                for job in jobs:
                    if job["user_id"] != api.uid:
                        raise ValueError("Pedido fora da conta autorizada.")
                    candidates.append((job["created_at"],index,api,job))
            except APIError as exc:
                if exc.status in (401,403):
                    print("Sessão da conta "+str(index+1)+" indisponível. A outra conta continua ativa; reinicie para reconectar.",flush=True)
                    unavailable.append(api)
                else:
                    print("Falha de conexão com uma conta:",str(exc),flush=True)
            except (URLError, TimeoutError):
                print("Sem conexão com uma conta. Tentarei novamente.",flush=True)
        for api in unavailable:
            accounts.remove(api)
        if not accounts:
            break
        if candidates:
            _, _, api, job = min(candidates,key=lambda item: (item[0],item[1]))
            try:
                process(api,pipeline,job)
            except APIError as exc:
                print("Não consegui iniciar o pedido:",str(exc),flush=True)
                time.sleep(12)
            except (URLError, TimeoutError):
                print("Conexão interrompida.",flush=True)
                time.sleep(12)
        else:
            time.sleep(12)
    print("Nenhuma conta conectada. Reinicie o programa para entrar novamente.")

if __name__=="__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nVESTE encerrado.")
