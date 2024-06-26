"""Platform for sensor integration."""
from __future__ import annotations

import asyncio

import voluptuous as vol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    PLATFORM_SCHEMA
)
import homeassistant.helpers.config_validation as cv
from homeassistant.const import UnitOfPower, UnitOfEnergy
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from apsystems_api import Api as ApApi
from apsystems_api import TokenExpired
from apsystems_api import DeviceOffline
from datetime import datetime

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    api = await ApApi.init(username=config[CONF_USERNAME], password=config[CONF_PASSWORD])

    devices = []
    inverters = await api.list_inverters()

    for inverter in inverters:
        devices.append(ApsystemsSensorNow(api, inverter))
        devices.append(ApsystemsSensorLifetime(api, inverter))
        devices.append(ApsystemsSensorToday(api, inverter))

    add_entities(devices, True)


class CurrentPower(SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "Current Output Power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_value = 0

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._attr_native_value = 23


class ApsystemsSensorNow(SensorEntity):
    """Representation of an APsystem sensor."""
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, api, inverter):
        """Initialize the sensor."""
        self._api = api
        self._inverter = inverter
        self._state = None
        self._name = f"APsystems {inverter.device_name} Power"
        self._device_class = SensorDeviceClass.POWER

    async def async_update(self):
        """Update the sensor data."""
        try:
            inverter_realtime = await self._api.get_inverter_realtime(self._inverter.inverter_dev_id)
            self._state = inverter_realtime.power
            return
        except TokenExpired:
            await self._api.refresh_login()
            await asyncio.sleep(3)
        except DeviceOffline:
            self._state = 0
            return
        inverter_realtime = await self._api.get_inverter_realtime(self._inverter.inverter_dev_id)
        self._state = inverter_realtime.power

        # inverter_statistic = await self._api.get_inverter_statistics(self._inverter.inverter_dev_id)
        # self._state = inverter_statistic.lastPower

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self) -> str | None:
        return f"apsystemsapi_{self._inverter.inverter_dev_id}_now"


class ApsystemsSensorLifetime(SensorEntity):
    """Representation of an APsystem sensor."""
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, api, inverter):
        """Initialize the sensor."""
        self._api = api
        self._inverter = inverter
        self._state = None
        self._name = f"APsystems {inverter.device_name} All-Time Production"
        self._device_class = SensorDeviceClass.POWER

    async def async_update(self):
        """Update the sensor data."""
        try:
            inverter_statistic = await self._api.get_lifetime_graph(self._inverter.inverter_dev_id)
            self._state = inverter_statistic.totalEnergy
        except TokenExpired:
            await asyncio.sleep(3)
            await self._api.refresh_login()
        inverter_statistic = await self._api.get_lifetime_graph(self._inverter.inverter_dev_id)
        self._state = inverter_statistic.totalEnergy

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self) -> str | None:
        return f"apsystemsapi_{self._inverter.inverter_dev_id}_lifetime"


class ApsystemsSensorToday(SensorEntity):
    """Representation of an APsystem sensor."""
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, api, inverter):
        """Initialize the sensor."""
        self._api = api
        self._inverter = inverter
        self._state = None
        self._name = f"APsystems {inverter.device_name} Today Production"
        self._device_class = SensorDeviceClass.POWER

    async def async_update(self):
        """Update the sensor data."""
        now = datetime.now()
        try:
            inverter_statistic = await self._api.get_graph(inverter=self._inverter.inverter_dev_id, year=now.year,
                                                           month=now.strftime('%m'), day=now.strftime('%d'))
            self._state = inverter_statistic.totalEnergy
        except TokenExpired:
            await asyncio.sleep(3)
            await self._api.refresh_login()
        inverter_statistic = await self._api.get_graph(inverter=self._inverter.inverter_dev_id, year=now.year,
                                                       month=now.strftime('%m'), day=now.strftime('%d'))
        self._state = inverter_statistic.totalEnergy

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self) -> str | None:
        return f"apsystemsapi_{self._inverter.inverter_dev_id}_today"
