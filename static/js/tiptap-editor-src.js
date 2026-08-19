import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";

const instances = new Map();

const toolbarGroups = [
  [
    { command: "undo", icon: "fa-undo", aria: "Undo" },
    { command: "redo", icon: "fa-redo", aria: "Redo" },
  ],
  [
    { command: "bold", icon: "fa-bold", aria: "Bold" },
    { command: "italic", icon: "fa-italic", aria: "Italic" },
    { command: "underline", icon: "fa-underline", aria: "Underline" },
    { command: "strike", icon: "fa-strikethrough", aria: "Strike" },
  ],
  [
    { command: "paragraph", icon: "fa-paragraph", aria: "Paragraph" },
    { command: "heading1", label: "H1", aria: "Heading 1" },
    { command: "heading2", label: "H2", aria: "Heading 2" },
    { command: "heading3", label: "H3", aria: "Heading 3" },
  ],
  [
    { command: "bulletList", icon: "fa-list-ul", aria: "Bullet list" },
    { command: "orderedList", icon: "fa-list-ol", aria: "Ordered list" },
    { command: "blockquote", icon: "fa-quote-right", aria: "Blockquote" },
  ],
  [
    { command: "link", icon: "fa-link", aria: "Create or edit link" },
    { command: "unlink", icon: "fa-unlink", aria: "Remove link" },
  ],
];

function isRelativeUrl(url) {
  return url.startsWith("/") || url.startsWith("#");
}

function normalizeUrl(value) {
  const url = value.trim();
  if (!url) {
    return "";
  }

  if (isRelativeUrl(url)) {
    return url;
  }

  const withProtocol = /^[a-z][a-z0-9+.-]*:/i.test(url) ? url : `https://${url}`;
  const parsed = new URL(withProtocol, window.location.origin);
  const allowedProtocols = ["http:", "https:", "mailto:", "tel:"];

  if (!allowedProtocols.includes(parsed.protocol)) {
    return null;
  }

  return withProtocol;
}

function setElementValue(element, value, triggerChange) {
  element.value = value;

  if (!triggerChange) {
    return;
  }

  if (window.jQuery) {
    window.jQuery(element).val(value).change();
    return;
  }

  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function getTargetTextarea(textarea) {
  const ref = textarea.dataset.ref;
  if (!ref) {
    return textarea;
  }

  return document.getElementById(ref) || textarea;
}

function syncInstance(instance, triggerChange = false) {
  const html = instance.editor.getHTML();
  setElementValue(instance.textarea, html, false);

  if (instance.target && instance.target !== instance.textarea) {
    setElementValue(instance.target, html, triggerChange);
  }
}

function createButton(config, editor, instance) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "tiptap-editor__button";
  button.dataset.command = config.command;
  button.setAttribute("aria-label", config.aria);
  button.title = config.aria;

  if (config.icon) {
    const icon = document.createElement("i");
    icon.className = `fas ${config.icon}`;
    icon.setAttribute("aria-hidden", "true");
    button.appendChild(icon);
  } else {
    button.textContent = config.label;
  }

  button.addEventListener("click", (event) => {
    event.preventDefault();
    runCommand(config.command, editor);
    updateToolbar(instance);
    syncInstance(instance, true);
  });

  return button;
}

function createToolbar(editor, instance) {
  const toolbar = document.createElement("div");
  toolbar.className = "tiptap-editor__toolbar";
  toolbar.setAttribute("role", "toolbar");

  toolbarGroups.forEach((group) => {
    const groupElement = document.createElement("div");
    groupElement.className = "tiptap-editor__button-group";

    group.forEach((config) => {
      groupElement.appendChild(createButton(config, editor, instance));
    });

    toolbar.appendChild(groupElement);
  });

  return toolbar;
}

function isActive(command, editor) {
  switch (command) {
    case "bold":
      return editor.isActive("bold");
    case "italic":
      return editor.isActive("italic");
    case "underline":
      return editor.isActive("underline");
    case "strike":
      return editor.isActive("strike");
    case "paragraph":
      return editor.isActive("paragraph");
    case "heading1":
      return editor.isActive("heading", { level: 1 });
    case "heading2":
      return editor.isActive("heading", { level: 2 });
    case "heading3":
      return editor.isActive("heading", { level: 3 });
    case "bulletList":
      return editor.isActive("bulletList");
    case "orderedList":
      return editor.isActive("orderedList");
    case "blockquote":
      return editor.isActive("blockquote");
    case "link":
    case "unlink":
      return editor.isActive("link");
    default:
      return false;
  }
}

function canRun(command, editor) {
  switch (command) {
    case "undo":
      return editor.can().undo();
    case "redo":
      return editor.can().redo();
    case "bold":
      return editor.can().chain().focus().toggleBold().run();
    case "italic":
      return editor.can().chain().focus().toggleItalic().run();
    case "underline":
      return editor.can().chain().focus().toggleUnderline().run();
    case "strike":
      return editor.can().chain().focus().toggleStrike().run();
    case "paragraph":
      return editor.can().chain().focus().setParagraph().run();
    case "heading1":
      return editor.can().chain().focus().toggleHeading({ level: 1 }).run();
    case "heading2":
      return editor.can().chain().focus().toggleHeading({ level: 2 }).run();
    case "heading3":
      return editor.can().chain().focus().toggleHeading({ level: 3 }).run();
    case "bulletList":
      return editor.can().chain().focus().toggleBulletList().run();
    case "orderedList":
      return editor.can().chain().focus().toggleOrderedList().run();
    case "blockquote":
      return editor.can().chain().focus().toggleBlockquote().run();
    case "unlink":
      return editor.isActive("link");
    case "link":
      return true;
    default:
      return false;
  }
}

function updateToolbar(instance) {
  const { editor, wrapper } = instance;

  wrapper.querySelectorAll(".tiptap-editor__button").forEach((button) => {
    const command = button.dataset.command;
    const active = isActive(command, editor);
    const enabled = canRun(command, editor);

    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.disabled = !enabled;
  });
}

function runCommand(command, editor) {
  switch (command) {
    case "undo":
      editor.chain().focus().undo().run();
      break;
    case "redo":
      editor.chain().focus().redo().run();
      break;
    case "bold":
      editor.chain().focus().toggleBold().run();
      break;
    case "italic":
      editor.chain().focus().toggleItalic().run();
      break;
    case "underline":
      editor.chain().focus().toggleUnderline().run();
      break;
    case "strike":
      editor.chain().focus().toggleStrike().run();
      break;
    case "paragraph":
      editor.chain().focus().setParagraph().run();
      break;
    case "heading1":
      editor.chain().focus().toggleHeading({ level: 1 }).run();
      break;
    case "heading2":
      editor.chain().focus().toggleHeading({ level: 2 }).run();
      break;
    case "heading3":
      editor.chain().focus().toggleHeading({ level: 3 }).run();
      break;
    case "bulletList":
      editor.chain().focus().toggleBulletList().run();
      break;
    case "orderedList":
      editor.chain().focus().toggleOrderedList().run();
      break;
    case "blockquote":
      editor.chain().focus().toggleBlockquote().run();
      break;
    case "link":
      setLink(editor);
      break;
    case "unlink":
      editor.chain().focus().unsetLink().run();
      break;
  }
}

function setLink(editor) {
  const previousUrl = editor.getAttributes("link").href || "";
  const input = window.prompt("URL", previousUrl);

  if (input === null) {
    editor.chain().focus().run();
    return;
  }

  const url = normalizeUrl(input);
  if (url === "") {
    editor.chain().focus().extendMarkRange("link").unsetLink().run();
    return;
  }

  if (url === null) {
    window.alert("URL no permitida");
    editor.chain().focus().run();
    return;
  }

  editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
}

function initTextarea(textarea) {
  if (!textarea || instances.has(textarea)) {
    return instances.get(textarea) || null;
  }

  const target = getTargetTextarea(textarea);
  const editorElement = document.createElement("div");
  const wrapper = document.createElement("div");
  const instance = {
    editor: null,
    editorElement,
    target,
    textarea,
    wrapper,
  };

  wrapper.className = "tiptap-editor";
  editorElement.className = "tiptap-editor__content";
  textarea.classList.add("tiptap-source-textarea");
  textarea.setAttribute("aria-hidden", "true");

  const editor = new Editor({
    element: editorElement,
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
        link: {
          autolink: true,
          defaultProtocol: "https",
          openOnClick: false,
          HTMLAttributes: {
            rel: "noopener noreferrer",
            target: "_blank",
          },
        },
      }),
    ],
    content: textarea.value || target.value || "",
    onUpdate: () => {
      syncInstance(instance, true);
    },
    onSelectionUpdate: () => {
      updateToolbar(instance);
    },
    onFocus: () => {
      wrapper.classList.add("is-focused");
    },
    onBlur: () => {
      wrapper.classList.remove("is-focused");
      syncInstance(instance, true);
    },
  });

  instance.editor = editor;
  wrapper.appendChild(createToolbar(editor, instance));
  wrapper.appendChild(editorElement);
  textarea.insertAdjacentElement("afterend", wrapper);
  instances.set(textarea, instance);
  syncInstance(instance, false);
  updateToolbar(instance);

  return instance;
}

function initAll(root = document) {
  root.querySelectorAll("textarea[data-tiptap-editor], textarea.active-editor").forEach((textarea) => {
    initTextarea(textarea);
  });
}

function syncAll(root = document, triggerChange = false) {
  instances.forEach((instance) => {
    if (root === document || root.contains(instance.textarea) || root.contains(instance.wrapper)) {
      syncInstance(instance, triggerChange);
    }
  });
}

function destroyTextarea(textarea) {
  const instance = instances.get(textarea);
  if (!instance) {
    return;
  }

  instance.editor.destroy();
  instance.wrapper.remove();
  textarea.classList.remove("tiptap-source-textarea");
  textarea.removeAttribute("aria-hidden");
  instances.delete(textarea);
}

function destroyRemovedEditors(node) {
  if (!(node instanceof Element)) {
    return;
  }

  if (instances.has(node)) {
    destroyTextarea(node);
  }

  instances.forEach((instance, textarea) => {
    if (node.contains(textarea) || node.contains(instance.wrapper)) {
      destroyTextarea(textarea);
    }
  });
}

function installDocumentHooks() {
  document.addEventListener(
    "submit",
    (event) => {
      syncAll(event.target, false);
    },
    true,
  );

  document.addEventListener(
    "click",
    (event) => {
      if (event.target.closest(".save, button[type='submit'], input[type='submit']")) {
        syncAll(document, false);
      }
    },
    true,
  );

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node instanceof Element) {
          initAll(node);
        }
      });

      mutation.removedNodes.forEach(destroyRemovedEditors);
    });
  });

  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initAll(document);
    installDocumentHooks();
  });
} else {
  initAll(document);
  installDocumentHooks();
}

window.CapsulaeTiptap = {
  destroyTextarea,
  initAll,
  initTextarea,
  syncAll,
};
