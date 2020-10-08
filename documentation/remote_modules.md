# Remote Modules {#remote_modules}

Using rpyc Qudi modules can be accessed from a remote computer like they were locally used.

## Requirements

* rpyc in version 4.0.2 has to be installed.

## Server Configuration

The Qudi instance where the actual module is running can provide access from a remote Qudi instance by setting up a server:

In the configuration file:

```
[global]
  module_server:
    - address: ''
    - port: 12345
    - certfile: 'path/to/ssl/certificate'
    - keyfile: 'path/to/ssl/key'
    - cacerts: 'path/to/ssl/cacerts'
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
cacerts: 'path/to/ssl/cacerts'
```

## Important Notes

* If `certfile` and `keyfile` are not specified, the connection is unencrypted and not authenticated.

## Certificate generation

To generate the server certificate use

```openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 -keyout server.key -out server.crt```

To generate the client certificate use

```openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 -keyout client.key -out client.crt```

### Notes
* You do not have the setup your own CA to sign certificates. Simply use the client certificate as `cacerts` on
  server side and the server certificate on client side. That way you obtain simple two way authentication between the
  server and one client.
* For `cacerts` you can concatenate multiple client certificates into a single file to authenticate multiple clients.
