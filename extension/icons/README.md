# Extension Icons

Place your extension icons here:
- `icon16.png` - 16x16px
- `icon48.png` - 48x48px
- `icon128.png` - 128x128px

You can create simple icons or use a tool like:
- https://www.favicon-generator.org/
- https://www.canva.com/

For now, the extension will work without icons (Chrome will use a default icon).

## Quick Icon Creation

You can create a simple colored square as a placeholder:

```bash
# Using ImageMagick (if installed)
convert -size 16x16 xc:#667eea icon16.png
convert -size 48x48 xc:#667eea icon48.png
convert -size 128x128 xc:#667eea icon128.png
```

Or use an online tool to generate icons from text/logo.
