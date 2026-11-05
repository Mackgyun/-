// 서비스 워커: 웹 푸시를 받아 PC 오른쪽 아래 팝업(Windows 알림)·휴대폰 알림으로 띄운다.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch { data = { body: event.data && event.data.text() }; }
  const title = data.title || "청년의사 브리핑";
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || "",
    tag: data.tag || undefined,
    renotify: !!data.tag,
    icon: "/static/icon-192.png",
    badge: "/static/icon-192.png",
    data: { url: data.url || "/" },
    requireInteraction: false,
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if (new URL(c.url).origin === self.location.origin) {
        await c.focus();
        c.navigate(url);
        return;
      }
    }
    await self.clients.openWindow(url);
  })());
});
