/** SSE framing is independent of network chunks, including split CRLF pairs. */
export function createEventStreamParser(onEvent: (name: string, data: unknown) => void) {
  let buffer = "";
  function dispatch(block: string) {
    let name = "message";
    const data: string[] = [];
    for (const line of block.split(/\r\n|\n|\r/)) {
      if (line.startsWith(":")) continue;
      const colon = line.indexOf(":");
      const field = colon < 0 ? line : line.slice(0, colon);
      const value = colon < 0 ? "" : line.slice(colon + 1).replace(/^ /, "");
      if (field === "event") name = value;
      if (field === "data") data.push(value);
    }
    if (data.length) onEvent(name, JSON.parse(data.join("\n")));
  }
  return {
    push(chunk: string) {
      buffer += chunk;
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r\n\r\n|\n\n|\r\r/.exec(buffer))) {
        dispatch(buffer.slice(0, boundary.index));
        buffer = buffer.slice(boundary.index + boundary[0].length);
      }
    },
    finish() {
      if (buffer.trim()) dispatch(buffer);
      buffer = "";
    },
  };
}
