# 空气果 1S Home Assistant 插件

## 接入方式

1. 在路由器自定义域名（DNS劫持，或其他名字）中设置***apn.airnut.com***指向自己的Home Assistant内网地址，比如我的是***192.168.123.4***，具体方法建议自行搜索。
2. 用[Easylink app](https://www.mxchip.com/easylink/)连接好WiFi后(空气果亮绿灯即连接成功)，双击退出WiFi连接模式。
3. 通过hacs安装，或者复制文件到custom_components
4. 进行如下配置

```
#这个是必须有的
airnut:
  #夜间是否更新
  is_night_update: False
  #夜间开始时间
  night_start_hour: 0001-01-01 23:00:00
  #夜间结束时间
  night_end_hour: 0001-01-01 06:00:00

#ip为空气果内网的ip地址，空气果1s共四项数据，分别写四个类型的传感器
sensor:
  - platform: airnut
    ip: "192.168.123.61"
    type: co2
  - platform: airnut
    ip: "192.168.123.61"
    type: temperature
  - platform: airnut
    ip: "192.168.123.61"
    type: humidity
  - platform: airnut
    ip: "192.168.123.61"
    type: pm25

#如果有第二个空气果，可以在下面继续，以此类推
  - platform: airnut
    ip: "192.168.123.62"
    type: co2
  - platform: airnut
    ip: "192.168.123.62"
    type: temperature
  - platform: airnut
    ip: "192.168.123.62"
    type: humidity
  - platform: airnut
    ip: "192.168.123.62"
    type: pm25

```

## 已知问题

1. 在关闭服务的时候无法释放端口。现象是重启ha时，每隔一次启动失败一次，ha日志中有“server got [Errno 98] Address in use”错误。临时的解决办法是再重启一次就好了。

## 其他

我不是利益相关方，只是二手产品购买者。

能抓到的消息格式都直接放在data文件中了，暂时只抓到了主动获取的包，自动上传的包没抓到。

有人能知道自动上传的消息格式就好了。

这一两天休息时间临时搞的，有大佬有时间可以帮忙改改，我python写的不咋样，应该还有bug，我有时间就改。😂

最后谢谢之前写斐讯M1局域网接入的大佬，[原贴地址](https://bbs.hassbian.com/thread-4952-1-1.html)
