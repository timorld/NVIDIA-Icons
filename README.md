# NVIDIA Icon Library — PowerPoint Add-in

A PowerPoint task pane add-in for browsing and inserting NVIDIA marketing icons,
built from a folder of local SVG files.

## Adding new icons

1. Drop new `.svg` files into `icons/`. The filename (minus `.svg`) becomes the
   icon's internal name, e.g. `m48-new-icon.svg` -> `m48-new-icon`.
2. Regenerate `taskpane.html`:
   ```
   python build.py
   ```
3. Bump the cache-busting version number in `manifest.xml` — find the two
   `?v=N` query strings (in `SourceLocation` and the `Taskpane.Url` bt:Url)
   and increment N. PowerPoint's embedded browser caches `taskpane.html` by
   URL, so without this step it may keep showing the old icon set even after
   you push new ones.
4. Commit and push `icons/`, `taskpane.html`, and `manifest.xml`:
   ```
   git add icons taskpane.html manifest.xml
   git commit -m "Add new icons"
   git push
   ```
5. In PowerPoint, close and reopen the task pane. If it still shows old
   icons, remove the add-in (My Add-ins → right-click → Remove) and re-add
   it from the Shared Folder catalog — that forces a full reload.

## One-time setup

### 1. Create the GitHub repo and push

```
git init
git remote add origin https://github.com/timorld/NVIDIA-Icons.git
git add .
git commit -m "Initial NVIDIA icon add-in"
git branch -M main
git push -u origin main
```

### 2. Enable GitHub Pages

On github.com, go to the repo -> **Settings** -> **Pages** -> under
"Build and deployment", set **Source** to "Deploy from a branch", branch
`main`, folder `/ (root)`, then Save. After a minute or two the site will be
live at:

```
https://timorld.github.io/NVIDIA-Icons/
```

Check that `https://timorld.github.io/NVIDIA-Icons/taskpane.html` loads in a
browser before sideloading — GitHub Pages can take a few minutes to publish
after the first push.

### 3. Sideload the add-in in PowerPoint

- **Windows**: Insert tab -> Add-ins -> My Add-ins -> Upload My Add-in ->
  select `manifest.xml`.
- **Mac**: Insert tab -> Add-ins -> My Add-ins -> gear icon -> Upload My
  Add-in -> select `manifest.xml`.
- **PowerPoint on the web**: Insert tab -> Add-ins -> Upload My Add-in ->
  select `manifest.xml`.

The "Icon Library" button appears on the Home tab.

## Files

- `icons/` — source SVGs, one file per icon. This is the only thing you edit.
- `build.py` — regenerates `taskpane.html` from `template.html` + `icons/`.
- `template.html` — the add-in UI/logic (search, categories, insert-as-PNG,
  insert-as-SVG). Don't need to touch this unless changing behavior.
- `taskpane.html` — generated file that PowerPoint actually loads. Always
  regenerate + commit this after touching `icons/`.
- `commands.html` — required stub function file for the ribbon button.
- `manifest.xml` — the add-in manifest you sideload into PowerPoint.
- `icon-16/32/64/80.png` — ribbon button icons.
