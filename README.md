# The DIY Battery
Forked from:
 - https://github.com/incub77/solis2mqtt
 - https://gist.github.com/markgdev/ce2dbf9002385cbe5a35b81985f9c84a
 - https://gist.github.com/madbobmcjim/5b8d42edce81893cd3ee47f9dfc8cbfd

Other Related Solis Modbus projects:
  - https://github.com/fboundy/ha_solis_modbus
  - https://github.com/hultenvp/solis-sensor (this relies on API calls to SolisCloud, which are a bit hit & miss)


Reference document for Solis registers (might be Solis firmware dependent):
 - https://www.scss.tcd.ie/Brian.Coghlan/Elios4you/RS485_MODBUS-Hybrid-BACoghlan-201811228-1854.pdf

**Website coming Soon:**
https://thediybattery.com

## Full Documentation Coming Soon :)

 - solis_5g_modbus_charge.py is designed to run as a background script in the main OS
(e.g.: nohup $HOME/solis_5g_modbus_charge.py & )

 - The Home Assistant instance is being run via supervised, which is considered to be the "Advanced installation" method; there's a detailed guide here showing how this is done:
  - https://peyanski.com/how-to-install-home-assistant-supervised-official-way/#Home_Assistant_Supervised_method
 - by doing this more convoluted HA installation, you get the flexibility of having a "full bells & whistles" HA instance, whilst also being able to run your mini PC/Raspberry Pi etc for other things too, including the solis_5g_modbus_charge.py script. I prefer this approach because sometimes a HA update can break things, so I prefer the code that communicates with the inverter to independent from HA (ie, greater robustness/reliability), especially when it comes to writing to the inverter for overnight charging.  
