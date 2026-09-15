apt-get install --reinstall -y grub-common grub-efi-amd64 shim-signed
update-initramfs -u -k all
update-grub
grub-install --target=x86_64-efi --efi-directory=/boot/efi --recheck
touch /.grub_updated
