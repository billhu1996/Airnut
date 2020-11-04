# 空气果 1S Home Assistant 插件

## 接入方式

1. 用官方app连接好WiFi后，空气果亮绿灯，app无反应（app就已经不重要了，结束使命了）
2. 在路由器中设置apn.airnut.com指向自己的ha内网地址，比如我的是192.168.123.4
3. 通过hacs安装，或者复制文件到custom_components
4. 进行如下配置
5. 将空气果音量调成0，否则每次检测都会出声音（将input_number.airnut_1s_volume这个值调成0）

```
input_number:
  airnut_1s_volume:
    name: 1S空气果
    icon: mdi:led-on
    initial: 0
    min: 0
    max: 100
    step: 1

sensor:
  - platform: airnut
    name: airnut1s
```

## 其他

我不是利益相关方，只是二手产品购买者。

能抓到的消息格式都直接放在data文件中了，暂时只抓到了主动获取的包，自动上传的包没抓到。

有人能知道自动上传的消息格式就好了。

这一两天休息时间临时搞的，有大佬有时间可以帮忙改改，我python写的不咋样，应该还有bug，我有时间就改。😂

最后谢谢之前写斐讯M1局域网接入的大佬，[原贴地址](https://bbs.hassbian.com/thread-4952-1-1.html)

