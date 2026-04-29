#!/usr/bin/env python3
"""
Nanoframe - Raspberry Pi HQ Camera (IMX477)
Bookworm 32-bit compatible
"""

import io, os, time, threading, json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder, H264Encoder
from picamera2.outputs import FileOutput

MEDIA_DIR = os.path.expanduser("~/media")
PORT      = 8000
os.makedirs(MEDIA_DIR, exist_ok=True)

# ── Stream output ────────────────────────────────────────
class StreamOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame     = None
        self.condition = threading.Condition()
    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

picam2     = Picamera2()
sout       = StreamOutput()
cam_lock   = threading.Lock()
rec_file   = [None]
state      = {"streaming": True, "recording": False}

def start_stream():
    cfg = picam2.create_video_configuration(
        main={"size": (1280, 960)},
        controls={"FrameRate": 30}
    )
    picam2.configure(cfg)
    picam2.start_recording(MJPEGEncoder(), FileOutput(sout))
    state["streaming"] = True

def restart_stream():
    try: picam2.stop_recording()
    except: pass
    time.sleep(0.5)
    start_stream()

# ── Threaded HTTP Server ─────────────────────────────────
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# ── HTML ─────────────────────────────────────────────────
PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nano Frame</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;height:100vh;overflow:hidden;display:flex;flex-direction:column}
header{background:#161b22;border-bottom:1px solid #30363d;padding:10px 18px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
header h1{font-size:15px;font-weight:600;color:#fff}
.tag{font-size:11px;padding:2px 9px;border-radius:20px;margin-left:8px;font-weight:500}
.tag-live{background:rgba(63,185,80,.15);color:#3fb950;border:1px solid rgba(63,185,80,.3)}
.tag-cam{background:rgba(88,166,255,.1);color:#58a6ff;border:1px solid rgba(88,166,255,.2)}
main{display:flex;flex:1;overflow:hidden}
.cam{flex:1;background:#000;position:relative;display:flex;align-items:center;justify-content:center}
.cam img{max-width:100%;max-height:100%;object-fit:contain}
.ovl{position:absolute;top:10px;left:10px;display:flex;gap:6px}
.badge{font-size:11px;padding:3px 9px;border-radius:4px;background:rgba(0,0,0,.72);border:1px solid rgba(255,255,255,.12);color:#fff}
.badge-rec{background:rgba(248,81,73,.75);animation:blink 1.2s infinite}
.badge-tl{background:rgba(227,179,65,.75)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}
.sbar{position:absolute;bottom:0;left:0;right:0;background:rgba(0,0,0,.65);padding:5px 12px;font-size:11px;color:#8b949e;display:flex;gap:20px}
.sbar span{color:#c9d1d9}
.flash{position:absolute;inset:0;background:#fff;opacity:0;pointer-events:none;transition:opacity .15s}
aside{width:275px;background:#161b22;border-left:1px solid #30363d;overflow-y:auto}
.sec{padding:13px 15px;border-bottom:1px solid #21262d}
.sec-t{font-size:10px;text-transform:uppercase;letter-spacing:.9px;color:#8b949e;font-weight:600;margin-bottom:10px}
button{width:100%;padding:9px 13px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;margin-bottom:6px;display:flex;align-items:center;justify-content:center;gap:7px;transition:all .15s}
button:last-child{margin-bottom:0}
button:active:not(:disabled){transform:scale(.97)}
button:disabled{opacity:.45;cursor:not-allowed}
.bb{background:rgba(88,166,255,.14);color:#58a6ff;border:1px solid rgba(88,166,255,.25)}
.bb:hover:not(:disabled){background:rgba(88,166,255,.26)}
.br{background:rgba(248,81,73,.14);color:#f85149;border:1px solid rgba(248,81,73,.25)}
.br:hover:not(:disabled){background:rgba(248,81,73,.26)}
.br.on{background:rgba(63,185,80,.18);color:#3fb950;border-color:rgba(63,185,80,.3)}
.bp{background:rgba(188,140,255,.12);color:#bc8cff;border:1px solid rgba(188,140,255,.22)}
.bp:hover:not(:disabled){background:rgba(188,140,255,.24)}
.bp.on{background:rgba(227,179,65,.14);color:#e3b341;border-color:rgba(227,179,65,.28)}
.bg{background:rgba(139,148,158,.1);color:#8b949e;border:1px solid #30363d}
.bg:hover:not(:disabled){background:rgba(139,148,158,.2);color:#c9d1d9}
select{width:100%;padding:7px 10px;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;font-size:12px;margin-bottom:8px;outline:none}
select:last-child{margin-bottom:0}
.sl{margin-bottom:9px}
.sl label{font-size:11px;color:#8b949e;display:flex;justify-content:space-between;margin-bottom:3px}
.sl label b{color:#c9d1d9;font-weight:500}
input[type=range]{width:100%;accent-color:#58a6ff;cursor:pointer}
.files{max-height:185px;overflow-y:auto}
.fi{display:flex;align-items:center;justify-content:space-between;padding:5px 8px;border-radius:5px;margin-bottom:3px;background:rgba(255,255,255,.03);border:1px solid #21262d}
.fi:hover{background:rgba(88,166,255,.07)}
.fi a{font-size:11px;color:#58a6ff;text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:158px}
.fi a:hover{text-decoration:underline}
.fi-s{font-size:10px;color:#8b949e;white-space:nowrap}
.empty{font-size:12px;color:#8b949e;text-align:center;padding:18px 0}
.toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%) translateY(50px);background:#161b22;border:1px solid #30363d;color:#c9d1d9;padding:9px 18px;border-radius:8px;font-size:13px;opacity:0;transition:all .28s;z-index:9999;white-space:nowrap;pointer-events:none}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.toast.ok{border-color:rgba(63,185,80,.5);color:#3fb950}
.toast.err{border-color:rgba(248,81,73,.5);color:#f85149}
.toast.info{border-color:rgba(88,166,255,.4);color:#58a6ff}
.spin{display:inline-block;width:11px;height:11px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:sp .6s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<header>
  <div style="display:flex;align-items:center">
    <h1>Nano Frame</h1>
    <span class="tag tag-live">● LIVE</span>
    <span class="tag tag-cam">IMX477 HQ</span>
  </div>
  <span style="font-size:12px;color:#8b949e" id="clk">--:--:--</span>
</header>
<main>
  <div class="cam">
    <img src="/stream.mjpg" id="stream">
    <div class="flash" id="flash"></div>
    <div class="ovl">
      <span class="badge" id="b-res">1280x960</span>
      <span class="badge badge-rec" id="b-rec" style="display:none">&#9210; REC</span>
      <span class="badge badge-tl"  id="b-tl"  style="display:none">&#8987; TL</span>
    </div>
    <div class="sbar">
      <div>Images <span id="s-img">0</span></div>
      <div>Videos <span id="s-vid">0</span></div>
      <div id="s-msg" style="color:#58a6ff"></div>
    </div>
  </div>
  <aside>
    <div class="sec">
      <div class="sec-t">Capture</div>
      <button class="bb" id="btn-img" onclick="captureImg()">
        &#128247; Capture Image
      </button>
      <button class="br" id="btn-vid" onclick="toggleVid()">
        &#9654; Start Video
      </button>
      <button class="bp" id="btn-tl" onclick="toggleTL()">
        &#9201; Timelapse
      </button>
    </div>
    <div class="sec">
      <div class="sec-t">Resolution &amp; Format</div>
      <select id="sel-res" onchange="document.getElementById('b-res').textContent=this.value">
        <option value="4056x3040">4056x3040 — Full 12MP</option>
        <option value="2028x1520">2028x1520 — 3MP</option>
        <option value="1920x1080">1920x1080 — 1080p</option>
        <option value="1280x960" selected>1280x960 — Default</option>
        <option value="640x480">640x480 — Fast</option>
      </select>
      <select id="sel-fmt">
        <option value="jpg">JPEG — smaller file</option>
        <option value="png">PNG — lossless</option>
      </select>
    </div>
    <div class="sec">
      <div class="sec-t">Camera Settings</div>
      <div class="sl"><label>Brightness <b id="v-br">0.0</b></label>
        <input type="range" id="r-br" min="-1" max="1" step="0.1" value="0" oninput="sv('v-br',this.value,1)" onchange="push()"></div>
      <div class="sl"><label>Contrast <b id="v-co">1.0</b></label>
        <input type="range" id="r-co" min="0" max="4" step="0.1" value="1" oninput="sv('v-co',this.value,1)" onchange="push()"></div>
      <div class="sl"><label>Saturation <b id="v-sa">1.0</b></label>
        <input type="range" id="r-sa" min="0" max="4" step="0.1" value="1" oninput="sv('v-sa',this.value,1)" onchange="push()"></div>
      <div class="sl"><label>Sharpness <b id="v-sh">1.0</b></label>
        <input type="range" id="r-sh" min="0" max="16" step="0.5" value="1" oninput="sv('v-sh',this.value,1)" onchange="push()"></div>
      <div class="sl"><label>Exposure (us) <b id="v-ex">Auto</b></label>
        <input type="range" id="r-ex" min="0" max="200000" step="1000" value="0" oninput="svEx(this.value)" onchange="push()"></div>
      <div class="sl"><label>Gain <b id="v-ga">Auto</b></label>
        <input type="range" id="r-ga" min="0" max="16" step="0.5" value="0" oninput="svGa(this.value)" onchange="push()"></div>
    </div>
    <div class="sec">
      <div class="sec-t">Files</div>
      <div class="files" id="file-list"><div class="empty">No files yet</div></div>
      <button class="bg" style="margin-top:8px" onclick="loadFiles()">&#8635; Refresh Files</button>
    </div>
  </aside>
</main>
<div class="toast" id="toast"></div>
<script>
let vidOn=false,tlOn=false,tlT=null,imgs=0,vids=0;
setInterval(()=>{document.getElementById('clk').textContent=new Date().toLocaleTimeString();},1000);

function toast(m,t='ok'){
  const el=document.getElementById('toast');
  el.textContent=m; el.className='toast show '+t;
  clearTimeout(el._h); el._h=setTimeout(()=>el.className='toast',3500);
}
function flash(){const f=document.getElementById('flash');f.style.opacity='.7';setTimeout(()=>f.style.opacity='0',160);}
function sv(id,v,dp){document.getElementById(id).textContent=parseFloat(v).toFixed(dp);}
function svEx(v){document.getElementById('v-ex').textContent=+v===0?'Auto':v+'us';}
function svGa(v){document.getElementById('v-ga').textContent=+v===0?'Auto':parseFloat(v).toFixed(1);}
function msg(m){document.getElementById('s-msg').textContent=m;}

function push(){
  fetch('/settings?brightness='+document.getElementById('r-br').value
    +'&contrast='+document.getElementById('r-co').value
    +'&saturation='+document.getElementById('r-sa').value
    +'&sharpness='+document.getElementById('r-sh').value
    +'&exposure='+document.getElementById('r-ex').value
    +'&gain='+document.getElementById('r-ga').value);
}

function captureImg(){
  const btn=document.getElementById('btn-img');
  if(btn.disabled)return;
  btn.disabled=true;
  btn.innerHTML='<span class="spin"></span> Capturing...';
  msg('Capturing...');
  const res=document.getElementById('sel-res').value;
  const fmt=document.getElementById('sel-fmt').value;
  fetch('/capture?res='+res+'&fmt='+fmt)
    .then(r=>r.json())
    .then(d=>{
      if(d.ok){flash();imgs++;document.getElementById('s-img').textContent=imgs;toast('Saved: '+d.file);loadFiles();}
      else toast('Error: '+(d.err||'unknown'),'err');
    })
    .catch(e=>toast('Failed: '+e,'err'))
    .finally(()=>{
      btn.disabled=false;
      btn.innerHTML='&#128247; Capture Image';
      msg('');
    });
}

function toggleVid(){
  const btn=document.getElementById('btn-vid');
  if(btn.disabled)return;
  btn.disabled=true;
  if(!vidOn){
    msg('Starting video...');
    fetch('/vid/start?res='+document.getElementById('sel-res').value)
      .then(r=>r.json())
      .then(d=>{
        if(d.ok){
          vidOn=true;
          btn.className='br on';
          btn.innerHTML='&#9632; Stop Video';
          document.getElementById('b-rec').style.display='';
          toast('Recording started','info');
        } else toast('Error: '+d.err,'err');
      })
      .catch(e=>toast('Failed: '+e,'err'))
      .finally(()=>{btn.disabled=false;msg('');});
  } else {
    msg('Stopping...');
    fetch('/vid/stop')
      .then(r=>r.json())
      .then(d=>{
        vidOn=false;
        btn.className='br';
        btn.innerHTML='&#9654; Start Video';
        document.getElementById('b-rec').style.display='none';
        vids++;document.getElementById('s-vid').textContent=vids;
        toast('Saved: '+d.file);loadFiles();
      })
      .catch(e=>toast('Failed: '+e,'err'))
      .finally(()=>{btn.disabled=false;msg('');});
  }
}

function toggleTL(){
  const btn=document.getElementById('btn-tl');
  if(!tlOn){
    const s=prompt('Interval in seconds?','5');
    if(!s||isNaN(s)||+s<1)return;
    tlOn=true;
    btn.className='bp on';
    btn.innerHTML='&#9632; Stop Timelapse';
    document.getElementById('b-tl').style.display='';
    toast('Timelapse every '+s+'s','info');
    const res=document.getElementById('sel-res').value;
    const fmt=document.getElementById('sel-fmt').value;
    tlT=setInterval(()=>{
      fetch('/capture?res='+res+'&fmt='+fmt+'&tl=1')
        .then(r=>r.json())
        .then(d=>{if(d.ok){imgs++;document.getElementById('s-img').textContent=imgs;loadFiles();}});
    },+s*1000);
  } else {
    clearInterval(tlT);tlT=null;tlOn=false;
    btn.className='bp';
    btn.innerHTML='&#9201; Timelapse';
    document.getElementById('b-tl').style.display='none';
    toast('Timelapse stopped');
  }
}

function loadFiles(){
  fetch('/files')
    .then(r=>r.json())
    .then(files=>{
      const el=document.getElementById('file-list');
      if(!files.length){el.innerHTML='<div class="empty">No files yet</div>';return;}
      el.innerHTML=files.map(f=>'<div class="fi"><a href="/dl/'+f.n+'" target="_blank">'+f.n+'</a><span class="fi-s">'+f.s+'</span></div>').join('');
    }).catch(()=>{});
}
loadFiles();
setInterval(loadFiles,15000);
</script>
</body>
</html>"""

# ── Request Handler ──────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a): pass

    def do_GET(self):
        p = self.path.split('?')[0]
        qs = {}
        if '?' in self.path:
            for kv in self.path.split('?')[1].split('&'):
                if '=' in kv:
                    k,v=kv.split('=',1); qs[k]=v

        if p == '/':
            self.html(PAGE)

        elif p == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age',0)
            self.send_header('Cache-Control','no-cache,private')
            self.send_header('Content-Type','multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with sout.condition:
                        sout.condition.wait()
                        frame = sout.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type','image/jpeg')
                    self.send_header('Content-Length',len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except: pass

        elif p == '/capture':
            res = qs.get('res','1280x960')
            fmt = qs.get('fmt','jpg')
            tl  = qs.get('tl','0') == '1'
            w,h = map(int, res.split('x'))
            prefix = 'tl_' if tl else 'img_'
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = f"{prefix}{ts}.{fmt}"
            fpath = os.path.join(MEDIA_DIR, fname)
            with cam_lock:
                try:
                    picam2.stop_recording()
                    time.sleep(0.4)
                    cfg = picam2.create_still_configuration(main={"size":(w,h)})
                    picam2.configure(cfg)
                    picam2.start()
                    time.sleep(0.5)
                    picam2.capture_file(fpath)
                    picam2.stop()
                    time.sleep(0.3)
                    restart_stream()
                    self.json({"ok":True,"file":fname})
                except Exception as e:
                    try: restart_stream()
                    except: pass
                    self.json({"ok":False,"err":str(e)})

        elif p == '/vid/start':
            res = qs.get('res','1280x960')
            w,h = map(int, res.split('x'))
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = f"vid_{ts}.h264"
            fpath = os.path.join(MEDIA_DIR, fname)
            with cam_lock:
                try:
                    picam2.stop_recording()
                    time.sleep(0.4)
                    cfg = picam2.create_video_configuration(main={"size":(w,h)})
                    picam2.configure(cfg)
                    enc = H264Encoder(bitrate=8000000)
                    picam2.start_recording(enc, fpath)
                    rec_file[0] = fname
                    self.json({"ok":True})
                except Exception as e:
                    try: restart_stream()
                    except: pass
                    self.json({"ok":False,"err":str(e)})

        elif p == '/vid/stop':
            fname = rec_file[0] or 'video.h264'
            with cam_lock:
                try:
                    picam2.stop_recording()
                    time.sleep(0.3)
                    rec_file[0] = None
                    restart_stream()
                    self.json({"ok":True,"file":fname})
                except Exception as e:
                    self.json({"ok":False,"err":str(e)})

        elif p == '/settings':
            try:
                ctrl = {
                    'Brightness': float(qs.get('brightness',0)),
                    'Contrast':   float(qs.get('contrast',1)),
                    'Saturation': float(qs.get('saturation',1)),
                    'Sharpness':  float(qs.get('sharpness',1)),
                }
                exp  = int(qs.get('exposure',0))
                gain = float(qs.get('gain',0))
                ctrl['AeEnable'] = (exp == 0)
                if exp  > 0: ctrl['ExposureTime'] = exp
                if gain > 0: ctrl['AnalogueGain'] = gain
                picam2.set_controls(ctrl)
            except: pass
            self.send_response(200); self.end_headers()

        elif p.startswith('/dl/'):
            fname = p[4:]
            fpath = os.path.join(MEDIA_DIR, fname)
            if os.path.isfile(fpath):
                ext = fname.rsplit('.',1)[-1].lower()
                ct = {'jpg':'image/jpeg','jpeg':'image/jpeg',
                      'png':'image/png','h264':'video/mp4',
                      'mp4':'video/mp4'}.get(ext,'application/octet-stream')
                with open(fpath,'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type',ct)
                self.send_header('Content-Length',len(data))
                self.send_header('Content-Disposition',f'attachment; filename="{fname}"')
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404); self.end_headers()

        elif p == '/files':
            out = []
            try:
                for f in sorted(os.listdir(MEDIA_DIR), reverse=True):
                    fp = os.path.join(MEDIA_DIR,f)
                    if not os.path.isfile(fp): continue
                    sz = os.path.getsize(fp)
                    s  = f"{sz/1048576:.1f}MB" if sz>1048576 else f"{sz//1024}KB"
                    out.append({"n":f,"s":s})
            except: pass
            self.json(out)

        else:
            self.send_response(404); self.end_headers()

    def html(self, content):
        b = content.encode()
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',len(b))
        self.end_headers(); self.wfile.write(b)

    def json(self, data):
        b = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',len(b))
        self.end_headers(); self.wfile.write(b)

# ── Run ──────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"\n  Nano frame ready at http://YOUR_PI_IP:{PORT}")
    print(f"  Media folder: {MEDIA_DIR}\n")
    start_stream()
    httpd = ThreadedHTTPServer(('0.0.0.0', PORT), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        try: picam2.stop_recording()
        except: pass