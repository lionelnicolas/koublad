# Failover Manager

## Introduction

Failover Manager is a small daemon which runs on two different servers (nodes) to handle high availability on a master/slave cluster, and performs failover actions if needed.

Each instance monitors UDP pings to detect that the other node is alive. If it's not the case, the instance can ping a third party to check its connectivity (sort of a dummy quorum-based implementation).


## Authors

**Lionel Nicolas**


## Copyright and license

Failover Manager is made available under the terms of the [GPLv3](http://www.gnu.org/licenses/gpl.html).

Copyright 2014 Lionel Nicolas <lionel.nicolas@nividic.org>

