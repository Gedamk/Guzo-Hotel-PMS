import GuzoAIPlatformPage from "./GuzoAIPlatformPage";

export default function App() {
  const path = window.location.pathname;
  const isLocalDevHost = window.location.host === "localhost:5174";

  if (path !== "/ai-platform" || isLocalDevHost) {
    window.location.replace("http://127.0.0.1:5174/ai-platform");
    return null;
  }

  return <GuzoAIPlatformPage />;
}
