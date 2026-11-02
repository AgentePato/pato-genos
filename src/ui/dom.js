// Mini helper para crear elementos. Los textos se insertan siempre como
// texto (nunca como HTML), así los nombres que escriba alguien no pueden
// inyectar código.

export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value == null || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key.startsWith('on') && typeof value === 'function') {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) el.setAttribute(key, '');
    else el.setAttribute(key, value);
  }
  appendChildren(el, children);
  return el;
}

function appendChildren(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : String(child));
  }
}

export function replaceContent(el, ...children) {
  el.replaceChildren();
  appendChildren(el, children);
}

// Solo deja pasar enlaces http(s) o rutas del propio sitio (nada de javascript:).
export function safeUrl(url) {
  try {
    const parsed = new URL(url, location.href);
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}
