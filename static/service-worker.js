self.addEventListener("install", function (e) {
  console.log("✅ Service Worker installed");
  e.waitUntil(
    caches.open("inventory-cache").then(function (cache) {
      return cache.addAll(["/"]);
    })
  );
});

self.addEventListener("fetch", function (e) {
  e.respondWith(
    caches.match(e.request).then(function (response) {
      return response || fetch(e.request);
    })
  );
});
