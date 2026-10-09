# Corresponding compiler sources for TB 0.6.0

This release distributes an unmodified selection of MSYS2 UCRT64 compiler binaries. Every one of the 4,066 bundled compiler files was matched to its installed pacman package record. The corresponding sources, packaging patches and build recipes are supplied alongside the installer as **TB-Toolchain-Sources-0.6.0.zip** at https://github.com/3097729287/acm-agent-workflow/releases/tag/v0.6.0.

The source ZIP includes 14 exact official MSYS2 source-only archives for the 17 binary packages below, their original PKGBUILD and .SRCINFO, relevant upstream sources/signatures/Git object databases, SHA-256 checksums, package ownership inventories and original license texts. The GNU GCC 16.2.0-4 archive contains gcc-16.2.0.tar.xz, its GNU signature and all MSYS2 build patches. MinGW-w64 source commit 4564ee4b5063097bf747af3a3f8270a28adff820 and its complete Git object database were checked with git fsck.

No TB-specific compiler modifications were applied. Packaging only selected files and followed PE DLL dependencies. The compiler remains a separate executable; relevant runtime exceptions and all component license notices are preserved in compiler/ucrt64/share/licenses and THIRDPARTY.md.

| Binary package | Exact version/release | Source package | License from installed metadata |
| --- | --- | --- | --- |
| mingw-w64-ucrt-x86_64-binutils | 2.47-3 | mingw-w64-binutils | spdx:GPL-3.0-or-later AND GPL-2.0-or-later AND LGPL-3.0-or-later AND LGPL-2.0-or-later |
| mingw-w64-ucrt-x86_64-crt | 14.0.0.r426.g4564ee4b5-1 | mingw-w64-crt | spdx:ZPL-2.1 |
| mingw-w64-ucrt-x86_64-gcc | 16.2.0-4 | mingw-w64-gcc | spdx:GPL-3.0-or-later WITH GCC-exception-3.1 AND GFDL-1.3-or-later |
| mingw-w64-ucrt-x86_64-gettext-runtime | 1.0-1 | mingw-w64-gettext | spdx:GPL-3.0-or-later AND LGPL-2.1-or-later |
| mingw-w64-ucrt-x86_64-gmp | 6.3.0-2 | mingw-w64-gmp | LGPL3; GPL |
| mingw-w64-ucrt-x86_64-headers | 14.0.0.r426.g4564ee4b5-1 | mingw-w64-headers | spdx:ZPL-2.1 AND LGPL-2.1-or-later |
| mingw-w64-ucrt-x86_64-isl | 0.28-1 | mingw-w64-isl | spdx:MIT |
| mingw-w64-ucrt-x86_64-libgcc | 16.2.0-4 | mingw-w64-gcc | spdx:GPL-3.0-or-later WITH GCC-exception-3.1 AND GFDL-1.3-or-later |
| mingw-w64-ucrt-x86_64-libiconv | 1.19-1 | mingw-w64-libiconv | spdx:LGPL-2.1-or-later; documentation:spdx:GPL-3.0-or-later |
| mingw-w64-ucrt-x86_64-libstdc++ | 16.2.0-4 | mingw-w64-gcc | spdx:GPL-3.0-or-later WITH GCC-exception-3.1 AND GFDL-1.3-or-later |
| mingw-w64-ucrt-x86_64-libwinpthread | 14.0.0.r426.g4564ee4b5-1 | mingw-w64-winpthreads | spdx:MIT AND BSD-3-Clause-Clear |
| mingw-w64-ucrt-x86_64-mpc | 1.4.1-1 | mingw-w64-mpc | spdx:LGPL-3.0-or-later |
| mingw-w64-ucrt-x86_64-mpfr | 4.2.2-3 | mingw-w64-mpfr | spdx:LGPL-3.0-or-later |
| mingw-w64-ucrt-x86_64-windows-default-manifest | 20260815-1 | mingw-w64-windows-default-manifest | custom:Public Domain |
| mingw-w64-ucrt-x86_64-winpthreads | 14.0.0.r426.g4564ee4b5-1 | mingw-w64-winpthreads | spdx:MIT AND BSD-3-Clause-Clear |
| mingw-w64-ucrt-x86_64-zlib | 1.3.2-2 | mingw-w64-zlib | spdx:Zlib |
| mingw-w64-ucrt-x86_64-zstd | 1.5.7-2 | mingw-w64-zstd | spdx:BSD-3-Clause OR GPL-2.0-or-later |

## Official downloads and checksums

| Source archive | Bytes | SHA-256 |
| --- | ---: | --- |
| [mingw-w64-binutils-2.47-3.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-binutils-2.47-3.src.tar.zst) | 39009763 | `7f30f4c1624bb9a53f72b2b325d7560a730a7157faafbfc2242ddbaa4833118a` |
| [mingw-w64-crt-14.0.0.r426.g4564ee4b5-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-crt-14.0.0.r426.g4564ee4b5-1.src.tar.zst) | 54805035 | `8edb0c86c4fe776e6bda609149ef1b3bbbad772711796bd051c0d57318589d5c` |
| [mingw-w64-gcc-16.2.0-4.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-gcc-16.2.0-4.src.tar.zst) | 107228968 | `a1792a44764405bc365746e0e60f0daa122076cec0dddd35a781d141f94273cf` |
| [mingw-w64-gettext-1.0-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-gettext-1.0-1.src.tar.zst) | 10267655 | `cca0d0c8f60353faccc5ad40405240014e4a7ccc8b1c6ca9f4626aef3097d26e` |
| [mingw-w64-gmp-6.3.0-2.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-gmp-6.3.0-2.src.tar.zst) | 2097066 | `f288f944fd9609db220bcf6a8dd0703a5674eeb906ef35eb8485bb8192135994` |
| [mingw-w64-headers-14.0.0.r426.g4564ee4b5-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-headers-14.0.0.r426.g4564ee4b5-1.src.tar.zst) | 54807433 | `205f4aaf65442c4ae5cd199f519c353f472a5ca1786adf351d48f318c6c6b1e5` |
| [mingw-w64-isl-0.28-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-isl-0.28-1.src.tar.zst) | 1944224 | `889246cdeb8b3f731010b2c63edc16ee75a7a0e7336d267fa071710d11751b05` |
| [mingw-w64-libiconv-1.19-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-libiconv-1.19-1.src.tar.zst) | 5131029 | `74428280c17094da5b702c29b2e1a0abae59556ea5dfdd65705cc8ccc1e000fb` |
| [mingw-w64-mpc-1.4.1-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-mpc-1.4.1-1.src.tar.zst) | 533531 | `655ed4227108f08f129a0900850ab16330c2e2ad45105900d4327f036ace3a5f` |
| [mingw-w64-mpfr-4.2.2-3.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-mpfr-4.2.2-3.src.tar.zst) | 1507413 | `c8c9b1e091b744165b150d59b7599bcf014fe9c3ae21df98fd3807f05f702c60` |
| [mingw-w64-windows-default-manifest-20260815-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-windows-default-manifest-20260815-1.src.tar.zst) | 1973 | `bed6d206e13c6ef0149f59fb7ed0a20c8665b8f39297247aded467860830f954` |
| [mingw-w64-winpthreads-14.0.0.r426.g4564ee4b5-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-winpthreads-14.0.0.r426.g4564ee4b5-1.src.tar.zst) | 54807189 | `5493832de1b7e24f09edb556ed409091b0844f9677212c4865618d6f93c508be` |
| [mingw-w64-zlib-1.3.2-2.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-zlib-1.3.2-2.src.tar.zst) | 1326375 | `eef69dea52357e01b272d6fd6dc4d7c0773f71260cb7bcde6047c8c383518db3` |
| [mingw-w64-zstd-1.5.7-2.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-zstd-1.5.7-2.src.tar.zst) | 2402010 | `306797282df799e95d550e6d0bb4b0a7b848027b8e13893a24236e060837c217` |

## Inspect or rebuild

Extract this ZIP, then unpack the desired .src.tar.zst archive with tar --zstd. Preserve the whole extracted package directory, including PKGBUILD, .SRCINFO, patches and any upstream archive or Git mirror. The official package recipes are unchanged. Use a compatible MSYS2 environment with the UCRT64 toolchain/build dependencies listed in PKGBUILD and run makepkg-mingw under UCRT64. No binary-identical build is claimed; MSYS2 provides the original build configuration and packaging metadata.

For the MinGW-w64 packages, the source tarballs contain a bare Git mirror rather than a checked-out source tree. The recipe obtains the pinned commit from that mirror. It can also be inspected with git --git-dir=mingw-w64 show 4564ee4b5063097bf747af3a3f8270a28adff820:<path>. The full pinned source and build recipe are included, not just internet pointers.

Primary distribution: https://packages.msys2.org/ and https://mirror.msys2.org/mingw/sources/. Packaging repository: https://github.com/msys2/MINGW-packages. Build instructions: https://www.msys2.org/wiki/Creating-Packages/. GNU GCC licensing/runtime exception: https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html. Those upstream terms apply to their respective components; TB application source remains under its MIT license.
