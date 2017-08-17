#!/usr/bin/env python
# CollectD ProxySQL plugin
#
# Configuration:
#  Import proxysql
#  <Module proxysql>
#      Host localhost
#      Port 6032 (optional)
#      User admin
#      Password xxxx
#   Verbose true (optional, to enable debugging)
#  </Module>
#
# Requires "MySQLdb" for Python
#
# Author: Matthias Crauwels <matthias.crauwels@ugent.be>
# Based on
#  - https://github.com/chrisboulton/collectd-python-mysql by Chris Boulton <chris@chrisboulton.com>
#  - https://github.com/percona/proxysql_exporter by Percona
#
# License: MIT (http://www.opensource.org/licenses/mit-license.php)
#

import collectd
import re
import MySQLdb

PROXYSQL_CONFIG = {
    'Host':           'localhost',
    'Port':           6032,
    'User':           'admin',
    'Password':       '',
    'Verbose':        False,
}

PROXYSQL_STATUS_VARS = {
    'Active_Transactions': 'gauge',
    'Client_Connections_aborted': 'counter',
    'Client_Connections_connected': 'gauge',
    'Client_Connections_created': 'counter',
    'Client_Connections_non_idle': 'gauge',
    'ProxySQL_Uptime': 'counter',
    'Questions': 'counter',
    'Slow_queries': 'counter',
}

PROXYSQL_CONNECTION_POOL_STATS = {
	'status': 'absolute',
	'ConnUsed': 'gauge',
	'ConnFree': 'gauge',
	'ConnOK': 'counter',
	'ConnERR': 'counter',
	'Queries': 'counter',
	'Bytes_data_sent': 'counter',
	'Bytes_data_recv': 'counter',
	'Latency_us': 'gauge',
}


def get_mysql_conn():
    return MySQLdb.connect(
        host=PROXYSQL_CONFIG['Host'],
        port=PROXYSQL_CONFIG['Port'],
        user=PROXYSQL_CONFIG['User'],
        passwd=PROXYSQL_CONFIG['Password']
    )

def mysql_query(conn, query):
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(query)
    return cur

def fetch_proxysql_status(conn):
    result = mysql_query(conn, 'SELECT Variable_Name, Variable_Value FROM stats_mysql_global')
    status = {}
    for row in result.fetchall():
        status[row['Variable_Name']] = row['Variable_Value']

    return status

def fetch_proxysql_connection_pool_stats(conn):
    result = mysql_query(conn, 'SELECT hostgroup, srv_host, srv_port, * FROM stats_mysql_connection_pool')
    stats = {}
    for row in result.fetchall():
        hostgroup = row['hostgroup']
        server_key = row['srv_host'] + ':' + row['srv_port']

        if not stats.has_key(hostgroup):
            stats[hostgroup] = {}

        if not stats[hostgroup].has_key(server_key):
            stats[hostgroup][server_key] = {}

        status_values = {
            'ONLINE': 1,
            'SHUNNED': 2,
            'OFFLINE_SOFT': 3,
            'OFFLINE_HARD': 4
        }
        stats[hostgroup][server_key]['status'] = status_values.get(row['status'])

        fields = ['ConnUsed', 'ConnFree', 'ConnOK', 'ConnERR', 'Queries', 'Bytes_data_sent', 'Bytes_data_recv', 'Latency_us']
        for field in fields:
            stats[hostgroup][server_key][field] = row[field]

    return stats

def log_verbose(msg):
    if PROXYSQL_CONFIG['Verbose'] == False:
        return
    collectd.info('proxysql plugin: %s' % msg)

def dispatch_value(prefix, key, value, type, type_instance=None, plugin='proxysql'):
    if not type_instance:
        type_instance = key

    log_verbose('Sending value: %s/%s=%s' % (prefix, type_instance, value))
    if not value:
        return
    try:
        value = int(value)
    except ValueError:
        value = float(value)

    val               = collectd.Values(plugin=plugin, plugin_instance=prefix)
    val.type          = type
    val.type_instance = type_instance
    val.values        = [value]
    val.dispatch()

def configure_callback(conf):
    global PROXYSQL_CONFIG
    for node in conf.children:
        if node.key in PROXYSQL_CONFIG:
            PROXYSQL_CONFIG[node.key] = node.values[0]

    PROXYSQL_CONFIG['Port']    = int(PROXYSQL_CONFIG['Port'])
    PROXYSQL_CONFIG['Verbose'] = bool(PROXYSQL_CONFIG['Verbose'])

def read_callback():
    global PROXYSQL_STATUS_VARS, PROXYSQL_CONNECTION_POOL_STATS
    conn = get_mysql_conn()

    proxysql_status = fetch_proxysql_status(conn)
    for key in proxysql_status:
        if proxysql_status[key] == '': proxysql_status[key] = 0

        if key in PROXYSQL_STATUS_VARS:
            ds_type = PROXYSQL_STATUS_VARS[key]
        else:
            continue

        dispatch_value('status', key, proxysql_status[key], ds_type)

    # proxysql_connection_pool_stats = fetch_proxysql_connection_pool_stats(conn)
    # for hostgroup in proxysql_connection_pool_stats:
    #     hostgroup_connection_pool_stats = proxysql_connection_pool_stats[hostgroup]
    #
    #     for server_key in hostgroup_connection_pool_stats:
    #         server_connection_pool_stats = hostgroup_connection_pool_stats[server_key]
    #
    #         for key in server_connection_pool_stats:
    #
    #             if key in PROXYSQL_CONNECTION_POOL_STATS:
    #                 ds_type = PROXYSQL_CONNECTION_POOL_STATS[key]
    #             else:
    #                 continue
    #
    #             plugin_key = hostgroup + '-' + server_key + '-proxysql'
    #             dispatch_value('connection_pool_stats', key, server_connection_pool_stats[key], ds_type, None, plugin_key)

collectd.register_read(read_callback)
collectd.register_config(configure_callback)
