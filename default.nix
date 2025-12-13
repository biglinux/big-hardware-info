{
  python3Packages,
  gtk4,
  libadwaita,
  pkg-config,
  wrapGAppsHook4,
  gobject-introspection,
  inxi,
  pciutils,
  usbutils,
}:

python3Packages.buildPythonApplication {
  pname = "big-hardware-info";
  version = "2.0.0";

  src = ./.;

  pyproject = true;

  build-system = with python3Packages; [ uv-build ];
  dependencies = with python3Packages; [
    pygobject3
    pycairo
  ];

  nativeBuildInputs = [
    pkg-config
    wrapGAppsHook4
    gobject-introspection
  ];
  buildInputs = [
    gtk4
    libadwaita
    inxi
    pciutils
    usbutils
  ];

  postInstall = ''
    cp $src/usr/share $out/share -r
  '';
}
