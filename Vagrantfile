# -*- mode: ruby -*-
# vi: set ft=ruby :

boxes = {
  "host-01" => {
    :hostname   => "host-01",
    :private_ip => "192.168.56.11",
    :cpus       => "2",
    :memory     => "2048"
  }
}

bookworm_sources = <<-'BOOKWORM_SOURCES'
deb http://deb.debian.org/debian bookworm contrib main non-free-firmware
deb http://deb.debian.org/debian bookworm-updates contrib main non-free-firmware
deb http://deb.debian.org/debian bookworm-backports contrib main non-free-firmware
deb http://deb.debian.org/debian-security bookworm-security contrib main non-free-firmware
BOOKWORM_SOURCES

Vagrant.configure(2) do |config|
  boxes.each do |hostname, cfg|
    config.vm.box = "bento/debian-12-arm64"
      default = if hostname == "host-01" then true else false end
      config.vm.define hostname, primary: default do |config|
      config.vm.hostname = cfg[:hostname]
      config.vm.provider :vmware_fusion do |v|
        v.vmx["ethernet0.pcislotnumber"] = "160"
        v.vmx["ethernet1.pcislotnumber"] = "224"
        v.ssh_info_public = true
        v.linked_clone = false
        v.cpus = cfg[:cpus]
        v.memory = cfg[:memory]
      end
      config.vm.network "private_network", ip: cfg[:private_ip]
      config.vm.synced_folder ".", "/vagrant"
      config.vm.provision "shell", inline: "echo \"#{bookworm_sources}\" > /etc/apt/sources.list"
    end
  end
  if ARGV[0] == "up" then
    config.vm.provision "file", source: "~/.ssh/id_ed25519.pub", destination: "/home/vagrant/.ssh/id_ed25519.pub"
    config.vm.provision "shell", inline: "cat /home/vagrant/.ssh/id_ed25519.pub >> /home/vagrant/.ssh/authorized_keys"
  end
end
