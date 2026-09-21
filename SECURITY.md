# Security

This is a fully static site (no server-side code, no user accounts, no forms).

- All JavaScript libraries (Leaflet 1.9.4, Plotly.js 2.35.2) and fonts (Inter,
  Source Serif 4) are self-hosted in `vendor/`; pages load no third-party
  scripts or fonts. The only third-party request is OpenStreetMap map tiles.
- Every page sets a Content Security Policy (`<meta http-equiv>`) restricting
  scripts, connections, objects and forms to this site, and images to this
  site plus OpenStreetMap tiles.
- The contact e-mail address is assembled by JavaScript at load time.

To report a problem, e-mail the address on the site's Contact section or open a
GitHub issue (do not include sensitive information).
