import React from "react";

interface AIOSImageProps {
  src?: string;
  alt?: string;
  width?: string;
  height?: string;
}

export function AIOSImage({ src = "", alt = "", width, height }: AIOSImageProps) {
  return <img src={src} alt={alt} style={{ width, height, borderRadius: "8px" }} />;
}
