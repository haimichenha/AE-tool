# Sapphire Light3D + Mocha reconstruction protocol

## Scope and version lock

This is a source-only reconstruction protocol for the recorded **Sapphire 2024 Adobe** test baseline. It does not include any vendor binary. Supply matching, legitimately installed input files yourself. Do not run against a different version: every builder verifies a SHA-256 preimage and stops on mismatch.

Required baseline hashes:

| Input | SHA-256 |
|---|---|
| `lib64/sapphire_ae.dll` | `3A01082AD1D1F3189B9929B717BFD384FB5676BB0BC927F9E2141FAF54C07482` |
| `lib64/BorisFX.Sapphire.mocha.em64t/mocha4bcc.dll` | `969E1724C74FB4A661043E626FE92E8C29F062038C8D1BF647C99051F23DC029` |

The verified output fingerprints are recorded in `artifacts.manifest.json`; the binaries themselves are intentionally absent.

## Controlled lab layout

The recorded builders use `D:\tmp\sapphire-patch-lab` and isolated runtime roots below `D:\tmp\saprt`. Clone this repository to `D:\tmp\AE-tool`, then either adapt the path constants after reviewing them or create a working copy at the recorded lab path. Keep the original installation unchanged and create only a separate lab copy.

## Verified build chain

1. Put a verified baseline core at `D:\tmp\sapphire-patch-lab\sapphire_ae.dll`.
2. From `scripts/`, create the 54-title Light3D build:

   ```powershell
   py .\new_light3d_bulk_trial.py `
     --mapping ..\maps\Light3D-zh-CN-full.json `
     --destination D:\tmp\sapphire-patch-lab\trials\light3d_full_cp936_highbit\sapphire_ae.dll
   ```

   The script preserves internal keys, validates the `Light3D_Autogen` definition, uses the current Windows OEM code page for Chinese titles, and verifies the normalizer preimage/postimage.
3. Run `new_mocha_root_thunk_trial.py` to produce the root-thunk core. It requires the preceding output at its recorded path and yields the core fingerprint in `artifacts.manifest.json`.
4. Stage that core into a new isolated runtime using `New-IsolatedSapphireRuntime.ps1`. Its baseline check prevents replacement of the original installed core.
5. Run `new_mocha_menu_batch_trial.py` to build the UTF-8 Mocha UI copy. It validates 24 fixed-string preimages. Place only that generated UI copy into the isolated runtime's `lib64\BorisFX.Sapphire.mocha.em64t\mocha4bcc.dll` while Mocha is not running; keep a sibling backup before the replacement.
6. Create the distinct O_Light3D test identity from the matching installed source AEX (the recorded source SHA-256 is `888BB1C868D1DE4488FABDCF33CCB320400659329DC80F16FBB463B6B8F26D4C`):

   ```powershell
   .\New-IsolatedTestAex.ps1 `
     -SourceAex 'C:\Program Files\BorisFX\Sapphire 2024 Adobe\plugins64\Sapphire Plug-ins\Sapphire Lighting\S_Light3D.aex' `
     -DestinationAex 'D:\tmp\saprt\l3dao\plugins64\Sapphire Plug-ins\Sapphire Lighting\O_Light3D.aex' `
     -OriginalEffectName 'S_Light3D' `
     -TestEffectName 'O_Light3D' `
     -RuntimeRoot 'D:\tmp\saprt\l3dao'
   ```

   Copy that isolated test AEX—not an installed AEX—to the separate After Effects test plug-in directory.
7. With Mocha closed, back up the isolated runtime UI and copy the generated `trials\mocha_menu_batch_utf8\mocha4bcc.dll` to `D:\tmp\saprt\l3dao\lib64\BorisFX.Sapphire.mocha.em64t\mocha4bcc.dll`. Verify its SHA-256 matches `F5B853EFBEA11AAFB1FBD0226275301CD3758F21FA8A9FC25AA4BB3C0EF50FD1`.
8. Start After Effects and validate that the isolated test effect loads, Light3D labels render in Chinese, and Mocha's translated panel/menu items appear. Record the result separately; static checks alone do not prove UI runtime behavior.

## Known boundaries

- The documented result covers 54 Light3D parameter titles and 24 Mocha UI strings, not complete application localization.
- Chinese Light3D display depends on the OEM code-page handling recorded by the builder; the validated test environment used CP936.
- `new_mocha_wrapper_redirect_trial.py` is retained as an unsuccessful experiment. Do not use it in the reconstruction chain.
- All `observations/` files are evidence records; they are not executable inputs.
