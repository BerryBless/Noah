chrome.downloads.onCreated.addListener(async (downloadItem) => {
    const url = downloadItem.url;
    const parsed = new URL(url);
    const domain = parsed.hostname;
  
    console.log("[NOAH] 감지된 다운로드 URL:", url);
  
    chrome.cookies.getAll({ domain }, async (cookies) => {
      const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join("; ");
  
      try {
        const response = await fetch("http://localhost:8000/proxy-download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: url,
            cookie: cookieHeader,
            referer: parsed.origin  // 각 도메인에 맞는 Referer 자동 전송
          })
        });
  
        const result = await response.json();
        if (response.ok) {
          console.log("[NOAH] 서버 저장 성공:", result.file_name);
        } else {
          console.warn("[NOAH] 서버 응답 실패:", result);
        }
      } catch (err) {
        console.error("[NOAH] 서버 요청 중 오류:", err);
      }
    });
  });
  