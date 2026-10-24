"""Arnés E2E: servidor estático del repo + Firebase stubbed + datos de fixture.
Nunca toca producción: todo request a gstatic/Firebase/Google se intercepta."""
import json, threading, functools, http.server, socketserver, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"

class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def start_server(root=ROOT):
    h = functools.partial(_Q, directory=str(root))
    srv = socketserver.TCPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"

FB_APP = "export function initializeApp(c){return {c};}"
FB_STORE = """
const S=(window.__fb=window.__fb||{writes:[],remote:null,authed:false,authCalls:[]});
export function getFirestore(){return {};}
export function doc(){return {};}
export async function getDoc(){return {exists:()=>!!S.remote,data:()=>({data:S.remote})};}
export async function setDoc(_,v){S.writes.push(v);S.remote=v.data;}
export function onSnapshot(){return ()=>{};}
"""
FB_AN = "export function getAnalytics(){return {};}"
FB_AUTH = """
const S=(window.__fb=window.__fb||{writes:[],remote:null,authed:false,authCalls:[]});
const L=[];
export function getAuth(){return {get currentUser(){return S.authed?{email:S.email||'admin@test',uid:S.uid||'ylQ3m3XoCHTd0cwP7UQet7cSRpt1',getIdToken:async()=>"fixture-id-token"}:null;}};}
export async function signInWithEmailAndPassword(a,e,p){S.authCalls.push([e,p]);
  if(e===(S.okEmail||'admin@test')&&p===(S.okPass||'good-pass')){S.authed=true;S.email=e;L.forEach(f=>f(a.currentUser));return {user:a.currentUser};}
  const err=new Error('auth/invalid-credential');err.code='auth/invalid-credential';throw err;}
export function onAuthStateChanged(a,f){L.push(f);setTimeout(()=>f(a.currentUser),0);return ()=>{};}
export async function signOut(a){S.authed=false;L.forEach(f=>f(null));}
"""

import datetime as _dt, re as _re
REF = _dt.datetime(2026, 10, 19, 6, 0, tzinfo=_dt.timezone.utc)   # «ahora» del fixture

def fixture_jobs(age_hours=1):
    """Fixture con TODAS las fechas desplazadas para que «ahora» sea hace `age_hours` h:
    así los tests no dependen del día en que se ejecutan."""
    shift = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=age_hours) - REF
    def mv(m):
        d = _dt.datetime.strptime(m.group(0), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc) + shift
        return d.strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = (FIX / "jobs_fixture.json").read_text(encoding="utf-8")
    return json.loads(_re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", mv, raw))

def install_routes(page, jobs=None, extra_files=None):
    def fb(route):
        u = route.request.url
        body = FB_APP if "firebase-app" in u else FB_AN if "analytics" in u else FB_AUTH if "firebase-auth" in u else FB_STORE
        route.fulfill(status=200, content_type="text/javascript", body=body)
    page.route("https://www.gstatic.com/firebasejs/**", fb)
    page.route(lambda u: u.startswith("http") and "127.0.0.1" not in u and "gstatic.com/firebasejs" not in u,
               lambda r: r.abort())
    data = jobs if jobs is not None else fixture_jobs()
    page.route("**/data/jobs.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(data)))
    def _json_handler(payload):
        body = json.dumps(payload)
        return lambda route, request=None: route.fulfill(status=200, content_type="application/json", body=body)
    for pat, payload in (extra_files or {}).items():
        page.route(pat, _json_handler(payload))
