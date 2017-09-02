# Remote Modules

Using rpyc Qudi modules can be accessed from a remote computer like they were locally used.

## Requirements

* rpyc in at least version 3.3 has to be installed.

## Server Configuration

The Qudi instance where the actual module is running can provide access from a remote Qudi instance by setting up a server:

In the configuration file:

```
[global]
  remote_server:
    - address: ''
    - port: 12345
    - certfile: 'path/to/ssl/certificate'
    - keyfile: 'path/to/ssl/key'
```

To activate access to individual modules, add

```
remoteaccess: true
```

as an option to their configuration.

Using the `address` option the rpyc server can be bound to a specific interface. Specifing an empty string as in the example above will make the qudi server listening on all interfaces.

## Client Configuration

Specify a module in the configuration file as usual, but add the following options:

```
remote: 'rpyc://servername:port/module_name'
certfile: 'path/to/ssl/certificate'
keyfile: 'path/to/ssl/key'
```

## Important Notes

* If `certfile` and `keyfile` are not specified, the connection is unencrypted and not authenticated.
