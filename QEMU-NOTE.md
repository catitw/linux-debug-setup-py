# Booting in UEFI mode

> [Archlinux Wiki](https://wiki.archlinux.org/title/QEMU#Booting_in_UEFI_mode)

if you boot in UEFI mode, you must use `if=virtio` to specify your rootfs, and the device will named `/dev/vdx`.

eg:

```shell
qemu-system-x86_64 \
    -smp 1 \
    -m 4G \
    -drive if=virtio,file=/home/me/my-pros/make-linux-debug-py/archlinux.img,index=0,format=qcow2 \
    -kernel /home/me/my-pros/make-linux-debug-py/linux-build-6.10/arch/x86_64/boot/bzImage \
    -append "root=/dev/vda2 rw console=ttyS0 landlock=on nokaslr" \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
    -drive if=pflash,format=raw,file=/home/me/my-pros/make-linux-debug-py/.state/OVMF_VARS.4m.fd \
    -nographic
```

# Booting with KVM enabled

if you boot with KVM enabled, you must use `hb` to set breakpoint in GDB.
