# ProxySQL CollectD plugin

This repo contains the initial version for a CollectD plugin collecting ProxySQL metrics.
Currently this plugin collects only global stats, work needs to be done to also collect connection-pool stats.

## Installation

1. Install `MySQLdb` Python package (try `yum install MySQL-python` or `apt install python-mysqldb`)
2. Place proxysql.py in your CollectD python plugins directory
3. Configure the plugin in CollectD
4. Restart CollectD

## Configuration

If you don’t already have the Python module loaded, you need to configure it first:

```
<LoadPlugin python>
	Globals true
</LoadPlugin>
<Plugin python>
	ModulePath "/path/to/python/modules"
</Plugin>
```
You should then configure the ProxySQL plugin:

```
<Plugin python>
  Import proxysql
  <Module proxysql>
    Host localhost
    Port 6032 (optional)
    User admin
    Password xxxx
    Verbose true (optional, to enable debugging)
  </Module>
</Plugin>
```
