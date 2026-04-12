# Backlog

Deferred capabilities and known issues that are not current priority but need to be addressed later.

---

## Hover as prerequisite action

**Status**: deferred — not current priority, record only

### Problem

Some UI interactions require hover before the actual target becomes available:

- Hover on a table row to reveal action buttons (edit, delete)
- Hover on a menu item to open a submenu / cascader
- Hover on a trigger element to show a popover / tooltip / dropdown
- Hover on a navigation item to expand child links

In these cases hover is **not** a passive mouse-over — it is a **required step** that makes the subsequent click target exist in the DOM. Without performing the hover first, the click target is either hidden (`display: none`), not yet inserted into the DOM, or positioned off-screen.

### What needs to be supported later

**A. Execution layer**

Support an explicit `hover(target)` action that:
- Dispatches mouseenter/mouseover on the target
- Waits for the expected DOM change (node insertion, visibility toggle, etc.)
- Only then proceeds to the next step (e.g. click)

**B. Recording / analysis layer**

Identify when a hover is a prerequisite:
- A node appears (childList) or becomes visible (attribute/style change) immediately after a mouseover on a nearby trigger element
- The subsequent click targets the newly-appeared node
- The hover-then-click pair forms a causal sequence, not two independent actions

**C. Execution pattern**

```
hover(trigger)
  -> wait for expected change (submenu appears, button becomes visible)
  -> click(target inside newly appeared content)
  -> timeout / fallback if expected change doesn't arrive
```

This fits the existing mutation tracking infrastructure: hover triggers a DOM mutation, the executor waits for that mutation, then proceeds.

### Why not now

- Current phase focuses on stable mutation recording and AST association
- Hover detection requires mouseover/mouseenter event capture which is not yet in the recording pipeline
- Causal inference (hover caused this DOM change) depends on having the mutation tracking stable first
- The execution layer (action dispatch + wait + timeout) is future work
