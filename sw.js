const CACHE='veste-pwa-v6-1';
const ASSETS=['./','./index.html','./styles.css','./extra.css','./app.js','./manifest.webmanifest','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('veste-pwa-')&&k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
// Network-first for same-origin files to prevent stale app versions; offline cache fallback.
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  if(e.request.url==='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.119.0'){
    e.respondWith(caches.open(CACHE).then(async c=>{const old=await c.match(e.request);if(old)return old;const response=await fetch(e.request);if(response.ok)await c.put(e.request,response.clone());return response}));return;
  }
  if(new URL(e.request.url).origin!==self.location.origin)return;
  e.respondWith(fetch(e.request).then(res=>{
    if(res.ok){const copy=res.clone();e.waitUntil(caches.open(CACHE).then(cache=>cache.put(e.request,copy)))}
    return res;
  }).catch(()=>caches.match(e.request)));
});
