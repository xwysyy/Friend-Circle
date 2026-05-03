import type { FeedAdapter } from "./types.js";
import { renderRss } from "./lib/rss.js";

const adapter: FeedAdapter = {
  async build(_ctx) {
    return renderRss(
      { title: "Example", link: "https://example.com", description: "Example feed" },
      [],
    );
  },
};

export default adapter;
