# Strata on Linux (Dual Boot) for Coding

**Date**: 2026-10-12 (plan last revised 2026-10-11)  
**Status**: Plan only. Nothing has been installed on Linux yet.  
**Target Engine**: [Niko1221/Strata](https://github.com/Niko1221/Strata)  
**Related**: [strata.md](strata.md) (Windows 11 evaluation in this repository)

---

## 0. Key Facts

- **Source of truth**: the real project is [github.com/Niko1221/Strata](https://github.com/Niko1221/Strata) (MIT, built on llama.cpp/ggml). Its `README.md`, `docs/MODELS.md`, `docs/INSTALL.md` and `docs/MULTI_GPU.md` are the references for this plan.
- **stratallm.org is unofficial.** Its footer calls it "Unofficial Community Documentation", and it contradicts the real project (it lists Mixtral 8x22B, DeepSeek-V2-Lite and a `strata-cli run` command, none of which exist in the project's docs). Ignore it.
- **Hardware baseline**: AMD Ryzen 7 5800X3D, 32 GB DDR4-3200, NVIDIA RTX 3060 Ti 8 GB (Ampere, `sm_86`).
- **Possible upgrades, independent of each other**: 2x32 GB RAM (Addendum A) and a second GPU, RTX 2080 Ti 11 GB (Addendum B).
- **Dual-boot layout**: Ubuntu 24.04 LTS on a dedicated 1.6 TB SSD; Windows 11 stays on the fast NVMe and is never touched. Strata models live on a ~250 GB ext4 partition carved from the fast NVMe, mounted at `/mnt/strata`.

### Relation to the Windows Results in This Repository

[strata.md](strata.md) records the Windows 11 setup in this repository: Strata runs the `IQ2_XS` pack in low-RAM memory-mapped mode (`--low-ram mmap`, `configs/strata-iq2_xs.json`, `run-strata.bat`) at about 18 tok/s decode on the same 3060 Ti and 32 GB. The Linux plan targets the **Coder** (`IQ1_M`) size instead, because it is the only size that fits 32 GB without mapping experts from disk, and because Linux pins all expert memory (see Addendum B). Use the Windows numbers as the baseline to compare against after running `./bench.sh` on Linux.

---

## 1. What to Expect on the Baseline

How Strata works: it runs one model family (Qwen3.8-Flash-Next). The model's experts live in RAM, and the GPU caches the busiest ones. **RAM decides which size you can run. VRAM and disk speed decide how fast it runs.**

| | Baseline | Strata wants | Effect |
| :--- | :--- | :--- | :--- |
| RAM | 32 GB | 32 GB min, 64 GB for every size | Only the **Coder** size fits. Setup will most likely pick **low-RAM mode**, which maps the experts from disk instead of holding them all in RAM. |
| GPU | 3060 Ti 8 GB (Ampere) | 12 GB+ ("8 GB runs, slowly") | A small expert cache, so more of the work falls on the CPU and the disk. |
| Disk | Fast NVMe | NVMe strongly recommended | In low-RAM mode, **disk speed directly sets the speed**, so the models go on the fast NVMe. |

**Model: Coder** (ISTA-DASLab's coding version, `IQ1_M`).
- It keeps half the experts, chosen on code, and scores 91% of the full model on SWE-bench Verified (per its authors).
- It is weaker at non-code tasks and non-English text.
- At ~30 GB it is the only size that fits 32 GB.

**Speed**: usable but slow. The project's 55 tok/s figure for the Coder comes from a 12 GB card with 64 GB of RAM. On this baseline, use it for focused coding requests, not long agent loops. Measure with `./bench.sh`.

**Context**: start at 32K–64K. The TS project's agent rules (`AGENTS.md` plus `.agents/rules/*`) take a good chunk of that by themselves.

---

## 2. Step 0: Disk Layout

- **Linux** goes on the **dedicated 1.6 TB SSD**. Windows is never touched.
- **Strata models** go on an **ext4 partition carved from the fast NVMe**:
  1. In Windows Disk Management, shrink the Windows partition by **~250 GB**.
  2. Leave that space unallocated, and format it as ext4 from Linux (Step 3).

  Do not point Linux at the NTFS partition itself: Strata's memory-mapping and page-locking are slow and unreliable on NTFS under Linux. The existing Windows models under `models/` are therefore not shared with Linux.

## 3. Step 1: Prep in Windows

1. **Back up** anything that is not on GitHub.
2. **BitLocker / Device Encryption**: check *Settings > Privacy & security > Device encryption* (or run `manage-bde -status` as admin).
   - If it is on, save the **recovery key** from https://account.microsoft.com/devices/recoverykey somewhere off the PC.
   - Shrinking the partition or changing boot settings can trigger a recovery prompt.
3. **Turn off Fast Startup**: *Control Panel > Power Options > Choose what the power buttons do > uncheck "Turn on fast startup"*.
4. **Shrink the NVMe** by ~250 GB (Step 0).
5. Write the **Ubuntu 24.04 LTS** ISO to a USB stick (8 GB+) with **Rufus** or **balenaEtcher**.

## 4. Step 2: BIOS (AM4)

- Keep **UEFI** and **Secure Boot ON**. The NVIDIA driver install asks for a one-time password; on the next boot, choose *Enroll MOK* on the blue screen.
- **Bootloader**: GRUB should land only on the 1.6 TB SSD. The Ubuntu installer tends to reuse the first EFI partition it finds, which is Windows'. Either way works:
  - **Leave the NVMe connected**: choose *Manual installation*. On the 1.6 TB SSD, create a 1 GB *EFI System Partition* and an ext4 `/`, and set **"Device for boot loader installation" to the 1.6 TB SSD**. Do not touch any NVMe partition.
  - **Simplest**: disable the NVMe slot in the BIOS, or unplug it, for the install. *Erase disk and install* is then safe because only one disk is visible.

  After the first boot, check with `lsblk -o NAME,SIZE,MOUNTPOINT`: `/boot/efi` must be on the 1.6 TB SSD, not the NVMe.
- Optional: enable **Above 4G decoding / Resizable BAR**.

## 5. Step 3: Install Ubuntu 24.04

1. Boot from the USB stick, choose *Install Ubuntu*, then *Interactive*, and check *third-party graphics drivers* and *download updates*.
2. If the NVMe is disabled: choose *Erase disk and install* on the **1.6 TB SSD**. If it is connected: use *Manual installation* as in Step 2. Either way, confirm the disk model and size before clicking.
3. After the first boot:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   ubuntu-drivers list                       # pick 580 or newer
   sudo apt install -y nvidia-driver-580     # or the newest listed
   sudo reboot
   nvidia-smi                                # shows the 3060 Ti
   timedatectl set-local-rtc 1 --adjust-system-clock   # keeps Windows' clock right
   ```
4. If the NVMe was disabled, re-enable it. Then run `sudo update-grub`, and Windows appears in the boot menu.
5. **Strata partition**: open *Disks* (or GParted), select the 250 GB unallocated space on the NVMe, and create an **ext4** partition labelled `strata`. Then:
   ```bash
   sudo mkdir -p /mnt/strata
   sudo blkid | grep strata                  # copy its UUID
   echo 'UUID=<uuid> /mnt/strata ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
   sudo mount -a && sudo chown $USER /mnt/strata
   ```

## 6. Step 4: TS Project Dev Environment

```bash
sudo apt install -y git curl build-essential ripgrep gh
gh auth login                                   # browser login, sets git credentials
curl -fsSL https://fnm.vercel.app/install | bash && exec $SHELL
fnm install 20 && fnm default 20                # matches CI
# editor: VS Code .deb (code.visualstudio.com) or Antigravity's Linux build; browser: Chrome .deb or Firefox

git clone https://github.com/<owner>/<ts-project>.git ~/dev/ts-project && cd ~/dev/ts-project
npm ci                                          # `prepare` sets core.hooksPath=.githooks
ln -s ../.agents/skills .claude/skills          # Linux version of the junction in AGENTS.md
npm run verify && npm run dev
```

- **Keep one clone per OS** and sync through GitHub. `node_modules` holds per-OS binaries (esbuild, rollup), so do not share one folder between Windows and Linux.
- Windows-only bits in the TS project (PowerShell agent rules, the junction, `sync_data.ps1`, `rtk`) are tracked in the project's issue tracker.
- Until that issue is fixed: install `rtk`'s Linux build, and run `sync_data.ps1` through `pwsh` (`sudo snap install powershell --classic`).

## 7. Step 5: Strata

```bash
sudo apt install -y python3-venv
git clone https://github.com/Niko1221/Strata.git ~/Strata && cd ~/Strata
./setup.sh --data-dir /mnt/strata/Strata-data
#   model: Coder (setup recommends it at 32 GB); accept low-RAM mode if offered
#   context: 32K–64K to start; images: no
```

- **First start**: the PC may freeze for 1–3 minutes while it loads. Do not close the window.
- The app opens at `http://127.0.0.1:8080`.
- **Next time**: run `./setup.sh` to start it, and `./update.sh` to update it.
- Run `./bench.sh` once, and keep the report to compare after each addendum and against [strata.md](strata.md) section 8.
- **Optional, worth trying on the baseline**: `./setup.sh --calibrate` (15–30 min). It tunes the engine for the PC.
- **Leave VRAM for the desktop**: the 3060 Ti also drives the monitor. If the desktop stutters, use `./setup.sh --vram-reserve-mib 1000`. On an 8 GB card the engine already shrinks the default reserve to fit, so only raise it if needed.
- **Close unneeded browser tabs** while it runs. With 32 GB, Strata, `npm run dev`, and a browser compete for RAM.

## 8. Step 6: Coding Agent Against Strata

- **Claude Code**: run `ANTHROPIC_BASE_URL=http://127.0.0.1:8080 claude` inside `~/dev/ts-project`. The TS project repository's `.claude/settings.json` hooks run under node and work unchanged.
- **OpenAI-compatible tools** (Continue, Cline, Aider, OpenCode): base URL `http://127.0.0.1:8080/v1`, any key. The OpenCode settings in [strata.md](strata.md) section 9 apply unchanged, including the explicit `limit.context` needed for auto-compaction.
- **Thinking**: *off* or *low* for quick edits, *high* for hard bugs. Leave parallel requests at 1.

## 9. Rollback

Set Windows Boot Manager first in the BIOS boot order, or unplug the 1.6 TB SSD. The 250 GB partition can later be deleted and merged back into Windows from Disk Management.

---

## Addendum A: RAM Upgrade to 64 GB+

**This is the bigger upgrade of the two.** It takes Strata out of low-RAM mode, so the experts stop streaming from disk. It also unlocks the full models, and leaves room for a browser and the dev server.

### Hardware
1. Install the **2x32 GB** kit alone first, in the slots the motherboard manual names for two DIMMs (usually A2/B2).
2. In the BIOS, enable the **XMP/DOCP** profile (3200).
3. Run a memory test with **MemTest86** from a USB stick, or `memtester` in Linux for a quick check. Run at least one full pass.
4. **Optional, to reach 80 GB**: add two of the old 8 GB sticks (32+8 per channel) and re-test.
   - Four mixed DIMMs on AM4 often will not hold 3200. If the test fails, try 2933 or 2666.
   - If it still fails, go back to 64 GB. 64 GB already runs every size.

### Strata Changes
```bash
cd ~/Strata
./setup.sh --setup --low-ram off            # Coder now held fully in RAM, longer context
./setup.sh --setup --model IQ2_XS           # add a full model for general use (~70 GB more on /mnt/strata)
```

| RAM | Coding pick | General pick |
| :--- | :--- | :--- |
| 64 GB | **Coder** (fastest, up to 262K context) | **IQ2_XS** (recommended), or IQ3_XXS for higher quality |
| 80 GB | Coder | **IQ3_S** (best quality) with apps still open |

- Setup sees the new RAM and recommends again. Its choice can be accepted.
- With more than one model installed, `./setup.sh` asks which to start, and `run-<model>.sh` starts one directly.
- After switching, **disk speed matters much less**: the NVMe is read only at startup and for the 29 GB lookup table.
- Raise context to **128K** for long agent sessions on the TS project.
- Run `./bench.sh` again and compare.

**Disk space**: each extra full model adds ~70 GB. Shared files are not downloaded twice. 250 GB on `/mnt/strata` covers the Coder plus two full sizes.

---

## Addendum B: Second GPU (RTX 2080 Ti 11 GB)

### Before Installing
- **PSU**: the 3060 Ti (~200 W), 2080 Ti (~250–260 W), and 5800X3D add up to roughly a **quality 750 W** unit. Check for enough 8-pin PCIe connectors.
- **Slot and space**: on many B450/B550 boards the second x16 slot is x4 through the chipset. Strata says x4 is fine for its split. Check airflow, since two cards will be stacked.
- **Both cards qualify**: each card in a split must be RTX 20 or newer (compute 7.5+) with 8 GB+.

### Which Card Does What
- **Monitor**: plug it into the **3060 Ti**. The 2080 Ti then gives all its VRAM to Strata.
- **Speed**: the 2080 Ti has more VRAM and more compute units. Strata's `auto` order puts the faster card last, where the output head and draft layer run.
- **Overhead**: each card in a split keeps its own ~3.4 GB copy of the dense weights and ~1.5 GB of prompt buffers. On an 8 GB card that leaves little room for experts. **A split may not beat the 2080 Ti alone, so measure both.**

### Strata Changes
```bash
nvidia-smi                                  # note which number each card has
cd ~/Strata
./setup.sh                                  # it lists both cards and offers to share; say yes once to try
./bench.sh                                  # report 1: both cards
./setup.sh --gpu <2080Ti-number>            # this start only: 2080 Ti alone
./bench.sh                                  # report 2: 2080 Ti alone
```
Keep whichever is faster: `--gpus 0,1` (remembered) or `--gpu N`.

Split tuning to try, one at a time:
- `--prefill 1024` halves each card's prompt buffers, which frees VRAM on the 3060 Ti.
- `--vram-reserve-mib 1000 --vram-reserve-later-mib 300` leaves room for the desktop on the display card (the first card) only.
- `STRATA_STAGE_TRIM=1` with an explicit `--layer-split <K>` loads only each card's own layers' dense weights. It is opt-in and experimental. Start from the K that `auto` prints in the log.

**Why this is on Linux**: under Windows or WSL2, a split pins only 8 GiB of the expert memory, and the docs report that cost one two-card setup about two-thirds of its prompt speed. Linux pins all of it. This is also why the repository's Windows testing stays single-GPU.

### Combined with Addendum A
With 64 GB and both cards, the Coder's experts mostly fit across RAM plus the two GPU caches. This is the best setup this PC can reach. It can also run IQ2_XS comfortably for general use.
