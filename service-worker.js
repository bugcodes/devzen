const CACHE_NAME = "devzen-commute-v1";
const ASSETS = [
  "./",
  "./index.html"
];

// 1. 安装阶段：预缓存核心静态文件
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log("[Service Worker] 正在全量缓存极客离线闭包资产...");
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

// 2. 激活阶段：清理过期的缓存版本
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            console.log("[Service Worker] 清理历史缓存包:", key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// 3. 拦截与缓存代理：支持大厂漏洞流 API 离线自适应与静态极速秒开
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  // 针对漏洞流 API (/api/vulns)：网络优先，断网通勤自动降级使用缓存数据
  if (url.pathname === "/api/vulns") {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.status === 200) {
            const resClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, resClone);
            });
          }
          return response;
        })
        .catch(() => {
          console.log("[Service Worker] 进入无网通勤环境，已自动降级拦截为缓存漏洞库！");
          return caches.match(event.request);
        })
    );
  } else {
    // 针对主页等普通静态资源：缓存优先，网络更新
    event.respondWith(
      caches.match(event.request).then(cachedResponse => {
        if (cachedResponse) {
          // 静默异步获取最新，以确保下次刷新是最新的
          fetch(event.request).then(response => {
            if (response.status === 200) {
              caches.open(CACHE_NAME).then(cache => cache.put(event.request, response));
            }
          }).catch(() => {/* 忽略断网错误 */});
          return cachedResponse;
        }

        return fetch(event.request).then(response => {
          if (response.status === 200 && event.request.method === "GET") {
            const resClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, resClone);
            });
          }
          return response;
        });
      })
    );
  }
});
