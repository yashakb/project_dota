Flume: moving messages from queue to HDFS
=========================================

1. Download [Apache Flume](https://flume.apache.org/)
2. Build [flume-ng-rabbitmq](https://github.com/jcustenborder/flume-ng-rabbitmq) and copy built JAR to `flume/lib`
3. Start agent: `./apache-flume-1.6.0-bin/bin/flume-ng agent -Dflume.root.logger=DEBUG,console --conf ./apache-flume-1.6.0-bin/conf/ -flume-config.properties -n dota_matches_to_hdfs`

