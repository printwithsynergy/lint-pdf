// Re-export the opengraph-image so Twitter / X unfurls use the same artwork.
// Having a dedicated twitter-image.tsx makes Next.js emit the
// <meta name="twitter:image"> tag with a dedicated URL, which some
// crawlers prefer over the generic og:image.
export {
  runtime,
  alt,
  size,
  contentType,
  default,
} from "./opengraph-image";
