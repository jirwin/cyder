Cyder
=====

Django DNS/DHCP web manager.

Meant as a ground-up rewrite of Oregon State University's DNS/DHCP network web
manager, Maintain, which was previously built with PHP, this would be the fifth
coming of Maintain.

Cyder provides a web frontend built with user experience and visual design in
mind. It provides an easy-to-use and attractive interface for network
administrators to create, view, delete, and update DNS records and DHCP
objects.

On the backend are build scripts that generate DNS BIND files and DHCP builds
directly from the database backing Cyder. The database schema and backend
data models have been designed-to-spec using the RFCs.

![Cyder](http://i.imgur.com/p8Rmbvv.png)


Installation
============

###Dependencies (virtualenv recommended)

####Linux packages

- Fedora:

```
sudo yum install python-devel openldap-devel cyrus-sasl-devel openssl-devel python-pip community-mysql
sudo yum install community-mysql-devel community-mysql-server MySQL-python gcc rubygems bind
sudo systemctl start mysqld
```

- Debian:

<!-- TODO: add MySQL, pip, etc. -->

```
sudo apt-get install python-dev libldap2-dev libsasl2-dev libssl-dev rubygems
```

####Miscellaneous

```
sudo pip install django_cas
```

###Setup

- Clone the repo:

```
git clone 'git@github.com:OSU-Net/cyder.git'
cd cyder
```

- Install submodules and other dependencies and set up files:

```
git submodule update --init --recursive
pip install -r requirements/dev.txt
cp cyder/settings/local.py-dist cyder/settings/local.py
cp cyder/settings_test.py-dist cyder/settings_test.py
```

(Use settings_test.py when running tests.)

- Set up MySQL along with tables and data. Enter local database settings into `cyder/settings/local.py`.

- Sync and migrate the database:

<!-- clarify "migrate" -->

```
python manage.py syncdb
python manage.py migrate
```


- Pull jingo-minify for Django Sass support, and set up Sass CSS with Django:

```
cd vendor/src/jingo-minify && git pull origin master && cd -
sudo gem install sass
```

- Point our settings file towards the location of the Sass binary:

```
sed -i "s|SASS_BIN = '[^']*'|SASS_BIN = '`which sass`'|" cyder/settings/local.py
```

- Install a PEP8 linter as a git pre-commit hook:

```
git clone git@github.com:jbalogh/check && cd check
sudo python check/setup.py install
cp requirements/.pre-commit .git/hooks/pre-commit
```

Coding Standards
================

Adhere to coding standards, or feel the wrath of my **erupting burning finger**.

- [Mozilla Webdev Coding Guide](http://mozweb.readthedocs.org/en/latest/coding.html)
- Strict 80-character limit on lines of code in Python, recommended in HTML and JS
- 2-space HTML indents, 4-space indent everything else
- Single-quotes over double-quotes
- Use whitespace to separate logical blocks of code - no 200 line walls of code
- Reduce, reuse, recycle - this project is very generic-heavy, look for previously invented wheels
- Keep files litter-free: throw away old print statements and pdb imports
- Descriptive variable names - verbose > incomprehensible

For multi-line blocks of code, either use 4-space hanging indents or visual indents.

```
# Hanging Indent
Ship.objects.get_or_create(
    captain='Mal', address='Serenity', class='Firefly')

# Visual Indent
Ship.objects.get_or_create(captain='Mal', address='Serenity',
                           class='Firefly')
```
