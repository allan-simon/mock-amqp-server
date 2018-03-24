# -*- mode: ruby -*-
# vi: set ft=ruby ts=2 sw=2 expandtab :

PROJECT = "mock_amqp"

DOCKER_ENV = {
  "HOST_USER_UID" => Process.euid,
  "VIRTUAL_ENV_PATH" => "/tmp/virtual_env35",
}

ENV['VAGRANT_NO_PARALLEL'] = 'yes'
ENV['VAGRANT_DEFAULT_PROVIDER'] = 'docker'
Vagrant.configure(2) do |config|

  config.ssh.insert_key = false
  config.vm.define "dev", primary: true do |app|
    app.vm.provider "docker" do |d|
      d.image = "allansimon/allan-docker-dev-python"
      d.name = "#{PROJECT}_dev"
      d.has_ssh = true
      d.env = DOCKER_ENV
    end
    app.ssh.username = "vagrant"

    # so that we can git clone from within the docker
    app.vm.provision "file", source: "~/.ssh/id_rsa", destination: ".ssh/id_rsa"
    # so that we can git push from inside the docker
    app.vm.provision "file", source: "~/.gitconfig", destination: ".gitconfig"

    app.vm.provision "provisionning", type: "shell" do |s|
      s.env = DOCKER_ENV
      s.inline = "
        set -e
        set -u
        echo 'cd /vagrant' >> /home/vagrant/.zshrc
        chown vagrant:vagrant /home/vagrant/.zshrc

        python3 -m venv /tmp/virtualenv
        echo 'cd /vagrant' >> /home/vagrant/.zshrc
        set +u; source /tmp/virtualenv/bin/activate; set -u
        pip install --upgrade pip
        pip install h11
        chown -R vagrant:vagrant /tmp/virtualenv

        echo 'source /tmp/virtualenv/bin/activate' >> /home/vagrant/.zshrc
        chown vagrant:vagrant /home/vagrant/.zshrc
      "
    end

    app.vm.provision "print_help", type: "shell" do |s|
      s.inline = "
        echo 'done, you can now run `vagrant ssh` to connect to the service'
        echo '`python -m service` to run the service'
        echo '`py.test` to run the test'
      "
    end

  end

end
