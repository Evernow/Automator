import ssl, socket


# Key stores what we are checking, value stores what we expect.
check_if_blocked = {"events.gfe.nvidia.com" : "gfe.nvidia.com", "services.gfe.nvidia.com" : "services.gfe.nvidia.com",
                   "gfwsl.geforce.com" : "gfwsl.geforce.com",
                  "accounts.nvgs.nvidia.cn" : "sre.nvgs.nvidia.cn" , "telemetry.gfe.nvidia.com" : "gfe.nvidia.com",
                  "rds-assets.nvidia.com" : "services.gfe.nvidia.com"
                  }


def checkpiholes():
    string = ""
    for hostname in check_if_blocked.keys():
        try:
            ctx = ssl.create_default_context()  
            with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
                s.connect((hostname, 443))
                cert = s.getpeercert()
                subject = dict(x[0] for x in cert['subject'])
                issued_to = subject['commonName']
                if issued_to == check_if_blocked[hostname]: # Counters bullshit host or Pihole redirects.
                    string += "Successfully connected to " + hostname + "\n"
                else:
                        string += "Connection was redirected to " + issued_to + " when connecting to " + hostname + "\n"
        except Exception as f:
            string += "Failed to connect to " + hostname + " with " + str(f) + "\n"

    return(string)

