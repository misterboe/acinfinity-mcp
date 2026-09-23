# Complete endpoint inventory (from the Android app binary)

Source: `com.eternal.acinfinity` 2.0.8 (versionCode 123), decompiled with jadx 1.5.6 on 2026-09-23.
Every row is a Retrofit declaration from the app (`ic1.java` = DeviceApi, `p2`, `ty3`, `xq`, `lo4`,
`DeviceApiService`, `IpcApiService`). Paths are relative to `https://www.acinfinityserver.com/api/`
unless absolute. `Query` = URL query parameter (the app sends most writes as query strings),
`Field`/FORM = form body, `Body` = JSON body. The machine-readable list is
[`app-endpoints.json`](app-endpoints.json).

**179 distinct method+path pairs, 168 paths.** Status column: ✅ implemented here ·
📖 probed read-only · ⬜ not touched · 🔒 write, not attempted.

`minversion` header value comes from `getMinVersionHeader(devType)` = `"<devType>|3.5"` for H-family
devices (devType 19-22, 26, 27, 51), room-to-room fan (33), AC8K (39, 40), AirTap (48), circulation
fans (49, 50) and `"<devType>|"` otherwise; the interceptor splits it into `minversion` and `devType`
headers. Every request also carries `token`, `requestApp`, `version` (app version), `requestId` (ms
timestamp) and `sign` (see connection.md) once the account has a `secretId`.

## AI features

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| GET | `/api/dev/data/attentions` | `getAttentions` | Query:devId | – | `List<AttentionsBean>` | ⬜ |
| DELETE | `/api/dev/data/attentions/{devId}/{type}` | `deleteAttentions` | Path:devId, Path:type | – | `Void` | 🔒 |
| GET | `/api/dev/data/insightAC8K` | `getInsightAC8K` | Query:devId | – | `List<InsightsResult>` | ⬜ |
| POST | `/api/dev/ml` | `update` | Field | – | `Void` | 🔒 |
| GET | `/api/dev/ml/byDevId/{devId}` | `byDevId` | Path:devId | – | `List<NetMlInfo>` | ⬜ |
| PUT | `/api/dev/ml/dimLights` | `dimLights` | Query:devId | – | `–` | 🔒 |
| GET | `/api/dev/ml/insight` | `getAiInsightsByNet` | Query:devId, Query:seq, Query:mark | – | `List<AiInsightsNetBean>` | ⬜ |
| DELETE | `/api/dev/ml/insight/aiMsg` | `deleteAiInsight` | Query:devMacAddr, Query:seq, Query:trigger | – | `Void` | 🔒 |
| POST | `/api/dev/ml/insightForBle` | `getAiInsightsByBle` | Field, Query:devVersion | – | `List<AiInsightsNetBean>` | 🔒 |
| PUT | `/api/dev/ml/insightResult` | `setinsightResult` | Field, Query:devVersion | – | `Void` | 🔒 |
| GET | `/api/dev/ml/insightTime` | `getAiInsightsTimeByNet` | Query:devId, Query:seq | – | `RefreshTime` | ⬜ |
| PUT | `/api/dev/ml/insightTime/{devId}/{type}` | `setInsightTime` | Path:devId, Path:type, Query:timeStamp | – | `Void` | 🔒 |
| GET | `/api/dev/ml/insightTimeForBle` | `getAiInsightsTimeForBle` | Query:devMacAddr, Query:seq, Query:zoneId, Query:startTimeNight, Query:endTimeNight, Query:enctrNight | – | `Integer` | ⬜ |
| PUT | `/api/dev/ml/loadType` | `loadType` | Query:devId, Query:loadType | – | `Void` | 🔒 |
| POST | `/api/dev/ml/saveParams` | `saveLike` | Field | – | `Void` | 🔒 |
| GET | `/api/dev/ml/secFuc` | `getSecFucList` | Query:devId | – | `List<SecFun>` | 📖 |
| PUT | `/api/dev/ml/secFuc` | `setSecFuc` | Query | – | `Void` | 🔒 |
| DELETE | `/api/dev/ml/stageInfo` | `deleteStageInfo` | Query:devMacAddr, Query:seq, Query:msgType, Query:ignoreNextStageTips, Query:dayNum | – | `Void` | 🔒 |
| GET | `/api/dev/ml/stageInfo` | `getStageInfoByNet` | Query:devId, Query:seq | – | `List<NetStageInfo>` | ⬜ |
| POST | `/api/dev/ml/stageInfoForBle` | `getStageInfoForBle` | Field | – | `List<NetStageInfo>` | 🔒 |
| PUT | `/api/dev/ml/tentWork` | `tentWork` | Query:devId | – | `–` | 🔒 |
| POST | `/api/dev/ml/updateLoadType` | `updateLoadType` | Query:devId, Query:loadType, Query:port | – | `Void` | 🔒 |
| POST | `/api/ml/easymode/getMlRecipes` | `getMlRecipes` | – | – | `List<MlRecipesBean>` | 🔒 |
| POST | `/api/model/checkForApp` | `checkModelUpdate` | Body | – | `ModelCheckRes` | 🔒 |
| PUT | `dev/ml/restore` | `restoreML` | Field:devId | – | `Void` | 🔒 |

## Other

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| GET | `/api/dev/sensorSetting` | `getSensorSetting` | Query:devId | minversion | `NetDeviceSensorCali` | ⬜ |

## Camera (IPC)

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| DELETE | `/api/ipc/alert` | `deleteIpcAlert` | Query:devId, Query:type | – | `–` | 🔒 |
| PUT | `/api/ipc/alert` | `modifyIpcAlert` | Query:advId, Query:devId, Query:type, Query:number, Query:isOn, Query:lowSwitch, Query:highSwitch, Query:lowValue, Query:highValue, Query:lowValueF, Query:highValueF, Query:alarmBeep | – | `–` | 🔒 |
| PUT | `/api/ipc/alertStatus` | `updateAlertStatus` | Query:devId, Query:type, Query:isOn | – | `–` | 🔒 |
| GET | `/api/ipc/alerts` | `getIpcAlerts` | Query:devId | – | `–` | ⬜ |
| POST | `/api/ipc/bindingDevice` | `bindingDevice` | Query:devId, Query:ipcMac | – | `Void` | 🔒 |
| POST | `/api/ipc/closeKnowledge` | `closeKnowledge` | Query:id | – | `–` | 🔒 |
| POST | `/api/ipc/formattedSdCard` | `formattedSdCard` | Query:devId | – | `Void` | 🔒 |
| POST | `/api/ipc/getGptContent` | `getGptContent` | Query:id | – | `–` | ⬜ |
| POST | `/api/ipc/getGptContenti6` | `getChatGptContent` | Query:id | – | `–` | ⬜ |
| POST | `/api/ipc/getKnowledgeListi6` | `getKnowledgeList` | Query:devId | – | `–` | ⬜ |
| POST | `/api/ipc/getKnowledgeTab` | `getKnowledgeTab` | Query:devId | – | `–` | ⬜ |
| POST | `/api/ipc/getP2PInfo` | `getIpcInfo` | Query:devId | – | `IpcInfoBean` | ⬜ |
| POST | `/api/ipc/getServerIp` | `getServerIp` | – | – | `IpcServerBean` | ⬜ |
| POST | `/api/ipc/getSettingInfo` | `getSettingInfo` | Query:devId | – | `IpcSettingInfoBean` | ⬜ |
| POST | `/api/ipc/getTrendsPinned` | `getTrendsPinned` | Query:devId, Query:isLike | – | `–` | ⬜ |
| POST | `/api/ipc/getTrendsPinnedi6` | `getTrendsPinnedi6` | Query:devId, Query:isLike | – | `–` | ⬜ |
| POST | `/api/ipc/getUpgrade` | `getUpgrade` | Query:fFamily, Query:firmwareVersion, Query:hardwareVersion | – | `FirmwareVersion` | ⬜ |
| POST | `/api/ipc/getUpgradeProgress` | `getUpgradeProgress` | Query:devId | CONNECT_TIMEOUT:30000, READ_TIMEOUT:30000, WRITE_TIMEOUT:30000 | `–` | ⬜ |
| GET | `/api/ipc/intstr` | `getIntstr` | – | – | `–` | ⬜ |
| POST | `/api/ipc/isBindingSucceed` | `isBindingSucceed` | Query:appUserId | – | `IpcMacBean` | 🔒 |
| POST | `/api/ipc/loadAlarmLogs` | `getIpcAlarmLogs` | Query:appId, Query:devId, Query:pageNum, Query:pageSize, Query:id, Query:time | – | `–` | 🔒 |
| POST | `/api/ipc/lockUnlockIpc` | `lockUnlockIpc` | Query:devId, Query:lock | – | `Void` | 🔒 |
| POST | `/api/ipc/modIpcName` | `modifyIpcName` | Query:devId, Query:ipcName | – | `Void` | 🔒 |
| POST | `/api/ipc/pauseCamera` | `pauseCamera` | Query:devId, Query:pauseCamera | – | `–` | 🔒 |
| POST | `/api/ipc/photoLogs` | `getPhotoLogs` | Query:appId, Query:devId, Query:startTime, Query:endTime | – | `List<TimedPhotoBean>` | 🔒 |
| POST | `/api/ipc/photoLogsDate` | `getPhotoLogsDate` | Query:devId, Query:startTime, Query:endTime, Query:category | – | `–` | 🔒 |
| POST | `/api/ipc/querySdCardInfo` | `querySdCardInfo` | Query:devId | – | `IpcSdCardBean` | 🔒 |
| POST | `/api/ipc/rebootIpc` | `rebootIpc` | Query:devId | – | `Void` | 🔒 |
| POST | `/api/ipc/reset` | `resetIpc` | Query:devId | – | `–` | 🔒 |
| POST | `/api/ipc/sendLog` | `sendIpcLog` | Query:devId, Query:errorCode | – | `Object` | 🔒 |
| GET | `/api/ipc/sensorCalibration` | `getSensorCalibration` | Query:devId | – | `–` | ⬜ |
| PUT | `/api/ipc/sensorCalibration` | `sensorCalibration` | Query:devId, Query:leafTempCalF, Query:leafTempCal, Query:tempCalF, Query:tempCal, Query:humidCal | – | `–` | 🔒 |
| POST | `/api/ipc/setAiFeedBack` | `setAiFeedBack` | Query:devId, Query:knowledgeType, Query:ktSubType, Query:feedback | – | `–` | 🔒 |
| POST | `/api/ipc/setAiLike` | `setAiLike` | Query:devId, Query:knowledgeType, Query:ktSubType, Query:like | – | `–` | 🔒 |
| POST | `/api/ipc/setAiReset` | `setAiReset` | Query:devId | – | `–` | 🔒 |
| POST | `/api/ipc/setSubmit` | `setSubmitFeedback` | Query:devId, Query:knowledgeType, Query:ktSubType, Query:feedbackType | – | `–` | 🔒 |
| POST | `/api/ipc/setSyncForH` | `setSyncForH` | Query:devId, Query:isSync | – | `Void` | 🔒 |
| POST | `/api/ipc/setTrendsPinned` | `setTrendsPinned` | Query:devId, Body | – | `–` | 🔒 |
| POST | `/api/ipc/setting` | `updateSettingInfo` | Field | – | `Void` | 🔒 |
| POST | `/api/ipc/unbindingDevice` | `unbindingDevice` | Query:devId, Query:ipcMac | – | `Void` | 🔒 |
| POST | `/api/ipc/unbindingIpc` | `unbindingIpc` | Query:appUserId, Query:devId, Query:clearData | – | `Void` | 🔒 |
| POST | `/api/ipc/updateGptContent` | `updateGptContent` | Query:id, Query:content | – | `–` | 🔒 |
| POST | `/api/ipc/upload/deletePhotos` | `deletePhotos` | Body | – | `–` | 🔒 |
| POST | `/api/ipc/userConfirmUpgrade` | `userConfirmUpgrade` | Query:devId, Query:version, Query:fUrl, Query:size | – | `–` | 🔒 |
| DELETE | `ipc/alert` | `delIPCAlarmsById` | Query:devId, Query:type, Query:isOn | – | `Void` | 🔒 |
| POST | `ipc/alert` | `addIPCAlarms` | Query, Query:returnData | – | `NetAlarm` | 🔒 |
| PUT | `ipc/alert` | `updateIPCAlarmsById` | Query | – | `NetAlarm` | 🔒 |
| PUT | `ipc/alertStatus` | `updateIPCAlertStatus` | Query:devId, Query:type, Query:isOn | – | `Void` | 🔒 |
| POST | `ipc/loadAlarmLogs` | `getIpcAlarmLogs` | Query:appId, Query:devId, Query:id, Query:time, Query:pageSize, Query:pageNum | – | `NetLogData` | 🔒 |
| GET | `ipc/sensorCalibration` | `getIpcSensorCalibration` | Query:devId | – | `SensorCalibration` | ⬜ |
| PUT | `ipc/sensorCalibration` | `setIpcSensorCalibration` | Query:devId, Query:leafTempCalF, Query:leafTempCal, Query:tempCalF, Query:tempCal, Query:humidCal | timeout:5 | `Void` | 🔒 |

## App metadata

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| GET | `app/deviceTypeList` | `getDeviceTypeList` | – | – | `List<DeviceSeriesGroup>` | ⬜ |
| GET | `app/generalNotice` | `generalNotice` | Query:zoneId, Query:hasFamilyH | – | `MaintenanceNotice` | ⬜ |
| POST | `app/getApplogBy` | `getVersion` | Query:app_system, Query:app_version | – | `–` | 🔒 |
| POST | `app/grade` | `getGrade` | Query:grade | – | `Integer` | 🔒 |
| GET | `app/loadType` | `getLoadType` | Query:fFamily, Query:firmwareVersion | – | `List<LoadTypeData>` | ⬜ |
| GET | `app/sysNotice` | `sysNotice` | – | – | `MaintenanceNotice` | ⬜ |
| GET | `language/languageDataByVersion` | `getLanguageList` | Query:languageVersion, Query:lastTime | – | `LanguageResponse` | ⬜ |
| GET | `tags/list` | `getList` | – | – | `defpackage.el3` | ⬜ |

## Account, auth, sharing

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| POST | `auth/newToken` | `getNewToken` | Query:appEmail, Query:fcmToken | – | `UserInfo` | 🔒 |
| POST | `auth/refresh` | `refresh` | Query:refreshToken | – | `UserInfo` | 🔒 |
| POST | `email/sendEmail` | `sendEmail` | Query:appEmail | – | `Void` | 🔒 |
| POST | `email/sendEmailCodeIsOK` | `emailVerify` | Query:appEmail, Query:emailCode | – | `Void` | 🔒 |
| GET | `lwa/preAuth` | `getAccountLink` | – | – | `AccountLinkData` | ⬜ |
| POST | `user/addAPPUser` | `addAPPUser` | Query:appEmail, Query:appPasswordl | – | `UserInfo` | 🔒 |
| POST | `user/addAppDevInfo` | `bindDev` | Query:appUserId, Query:devMacAddr, Query:timeGmt, Query:zoneId, Query:devName, Query:devExternalVos, Query:advNameList, Query:alertNameList | minversion | `Void` | 🔒 |
| POST | `user/addUserFeedBack` | `addUserFeedBack` | Query:gradeId, Query:tagsId, Query:fbackEmail, Query:fbackTitle, Query:fbackText, Query:fbackInformation, Part | – | `Void` | 🔒 |
| POST | `user/appUserLogin` | `userLogin` | Query:appEmail, Query:appPasswordl, Query:fcmToken | – | `UserInfo` | ✅ |
| POST | `user/bindingDev` | `bindingDev` | Query:devMacAddr, Query:timeGmt, Query:zoneId, Query:devName, Query:devExternalVos, Query:advNameList, Query:alertNameList, Query:insideRoomName, Query:outsideRoomName, Query:deviceColor | minversion | `Void` | 🔒 |
| GET | `user/bindingDevResult` | `bindingDevResult` | Query:devMacAddr | minversion | `Long` | ⬜ |
| POST | `user/boarding` | `newBindingDevice` | Field:snCode, Field:appId, Field:devType, Field:firmwareVersion, Field:hardwareVersion, Field:requestId, Field:zoneId | – | `–` | 🔒 |
| GET | `user/boardingResult` | `isBindingSucceedNew` | Query:snCode | – | `–` | ⬜ |
| POST | `user/delAppDev` | `unbindDev` | Query:appUserId, Query:devId, Query:isDelAdvAll | minversion | `Void` | 🔒 |
| POST | `user/delAppShareDev` | `delShareDev` | Query:devId, Query:androidx.core.app.NotificationCompat.CATEGORY_EMAIL | – | `Void` | 🔒 |
| POST | `user/delDevNetWorkInfo` | `delDevNetWorkInfo` | Query:appUserId, Query:devMacAddr | minversion | `Void` | 🔒 |
| POST | `user/delShareDev` | `cancelShareDev` | Query:devId, Query:androidx.core.app.NotificationCompat.CATEGORY_EMAIL | – | `Void` | 🔒 |
| POST | `user/delUserInfo` | `delUserInfo` | Query:appId | – | `Void` | 🔒 |
| POST | `user/devInfoListAll` | `devInfoListAll` | Query:userId | – | `List<NetDevice>` | ✅ |
| POST | `user/devIsShareOk` | `acceptShare` | Query:id | – | `Void` | 🔒 |
| POST | `user/devShaerUserEmail` | `shareDev` | Query:userId, Query:appEmail, Query:devId | – | `Void` | 🔒 |
| POST | `user/devShareUser` | `shareWithOtherDevList` | Query:userId | – | `List<NetDevice>` | 🔒 |
| DELETE | `user/fcmToken` | `unregisterFcmToken` | Query:fcmToken | token | `Void` | 🔒 |
| POST | `user/fcmToken` | `registerFcmToken` | Query:fcmToken | – | `Void` | 🔒 |
| GET | `user/freeDevice` | `freeDevice` | Query:userId | – | `–` | ⬜ |
| POST | `user/getByUser` | `getByUser` | Query:appId | – | `UserInfo` | ⬜ |
| POST | `user/getByUserEmail` | `getByUserEmail` | Query:appEmail | – | `Void` | ⬜ |
| POST | `user/logout` | `logout` | Query:fcmToken | – | `Void` | 🔒 |
| POST | `user/shareDevList` | `shareWithYouDevList` | Query:userId | – | `List<NetDevice>` | 🔒 |
| POST | `user/updateAPPUser` | `updateAPPUser` | Query:appId, Query:appIsanalytics, Query:appIsbugreport, Query:appIsemailrepost | – | `String` | 🔒 |
| POST | `user/updateAPPUserPassword` | `updatePassword` | Query:appEmail, Query:appPasswordl | – | `Void` | 🔒 |

## Controllers & ports

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| POST | `dev/addAdvAlert` | `addAdvInfo` | Query | – | `Void` | 🔒 |
| POST | `dev/addDevMode` | `setModel` | Query | minversion, timeout:5 | `Void` | ✅ |
| POST | `dev/calibrationSensor` | `calibrationSensor` | Query:devId, Query:type, Query:sensorPort, Query:step, Query:operateType, Query:value | minversion | `Void` | 🔒 |
| POST | `dev/delADVInfo` | `delADVInfo` | Query:devId, Query:advId | timeout:5 | `Void` | 🔒 |
| POST | `dev/function` | `function` | Query:devId, Query:typeId, Query:fUrl, Query:unbindIpc | minversion | `Void` | 🔒 |
| POST | `dev/getDevSetting` | `getDevSetting` | Query:devId, Query:port | minversion | `NetDeviceSetting` | ✅ |
| POST | `dev/getDevTimeZone` | `getDevTimeZone` | – | – | `List<TimeZone>` | ⬜ |
| POST | `dev/getDeviceInfo` | `getDeviceInfo` | Query:devId | minversion | `NetDevice` | ⬜ |
| POST | `dev/getSockerIp` | `getSockerIp` | – | devType, minversion | `NetServe` | ⬜ |
| POST | `dev/getdevADVinfoBydevId` | `getADVInfoList` | Query:devId | – | `List<NetAdvance>` | ⬜ |
| POST | `dev/getdevModeSettingList` | `getModeSettingList` | Query:devId, Query:port | minversion | `NetDeviceMode` | ✅ |
| POST | `dev/initClockSetting` | `syncTime` | Query:appId | – | `Void` | 🔒 |
| PUT | `dev/modeAndSetting` | `updateModeAndSetting` | Query, Query:modeAndSettingIdStr | minversion | `Void` | ✅ |
| POST | `dev/netWorkSetting` | `netWorkSetting` | Query:devId, Query:wifiName, Query:wifiPwd | minversion | `Void` | 🔒 |
| POST | `dev/outletSwitch` | `outletSwitch` | Query:devId, Query:androidx.core.app.NotificationCompat.CATEGORY_STATUS | timeout:5 | `Void` | 🔒 |
| POST | `dev/putDevTimeZone` | `putDevTimeZone` | Query:devId, Query:timeZone | – | `Void` | 🔒 |
| PUT | `dev/restoreDevMode` | `restoreDevMode` | Field:devModeStr | minversion | `Void` | 🔒 |
| PUT | `dev/restoreDevSetting` | `restoreDevSetting` | Field:devSettingStr | minversion | `Void` | 🔒 |
| PUT | `dev/restoreModeAndSetting` | `restoreModeAndSetting` | Field:devId | minversion | `Void` | 🔒 |
| PUT | `dev/scene` | `updateScene` | Query:devId, Query:type, Query:scene, Query:sceneFeedback | minversion | `Void` | 🔒 |
| PUT | `dev/sceneBle` | `updateSceneBle` | Query:devMacAddr, Query:type, Query:scene, Query:sceneFeedback | minversion | `Void` | 🔒 |
| POST | `dev/updateADVStatus` | `updateADVStatus` | Query:devId, Query:advId | timeout:5 | `Void` | 🔒 |
| POST | `dev/updateAdvSetting` | `updateSetting` | Query | minversion | `Void` | ⚠️ std only |
| POST | `dev/updateMsterByNums` | `updateMsterPort` | Query:devId, Query:nums | minversion | `Void` | 🔒 |

## Other hosts / dev

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| POST | `http://192.168.0.238:8080/api/chat/question` | `chatMessage1` | Query:chatId, Query:message, Query:token | – | `–` | 🔒 |
| POST | `http://192.168.0.67/write/` | `write` | Field | timeout:5 | `String` | 🔒 |
| GET | `http://chatbox-us.acinfinityserver.com/api/application/b6af55a8-e9b1-11ef-b4c7-0afff3eb6ed3/chat/open` | `getChatId` | – | – | `–` | ⬜ |
| POST | `http://chatbox-us.acinfinityserver.com/api/application/chat_message/{id}` | `chatMessage` | Path:id, Body | – | `–` | 🔒 |

## History & logs

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| DELETE | `log/data` | `deleteData` | Query:devId, Query:time | devType | `Void` | ⬜ |
| POST | `log/dataPage` | `getDataListPage` | Query:appId, Query:devId, Query:time, Query:pageSize | – | `NetHistoryData` | 📖 |
| DELETE | `log/log` | `deleteLog` | Query:devId, Query:time | devType | `Void` | ⬜ |
| POST | `log/logdataByAll` | `getLogList` | Query:appId, Query:devId, Query:id, Query:time, Query:pageSize | – | `NetLogData` | 📖 500 |

## Firmware / OTA / backup

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| POST | `ota/getUpgrade` | `getChildOtaInfo` | Query:type, Query:firmwareVersion, Query:command | – | `ChildFirmwareVersion` | 🔒 |
| POST | `ota/initOtaUpgrade` | `otaUpgrade` | Query:version, Query:port, Query:subDeviceId, Query:fileUrl, Query:devId, Query:subDeviceType, Query:devMacAddr | – | `Map<String, Object>` | 🔒 |
| POST | `ota/otaUpgradeResult` | `otaUpgradeResult` | Query:devId, Query:port | – | `OtaResult` | 🔒 |
| POST | `ota/retryOtaUpgrade` | `retryOtaUpgrade` | Query:devId, Query:port | – | `Void` | 🔒 |
| DELETE | `upgrade/backup` | `deleteBackup` | Query:devMacAddr | minversion | `Void` | 🔒 |
| GET | `upgrade/backup` | `getBackup` | Query:devMacAddr, Query:devVersion | minversion | `BackupData` | ⬜ |
| POST | `upgrade/backup` | `addBackup` | Query:devMacAddr, Query:devVersion, Query:data, Query:firmwareVersion, Query:fFamily, Query:hardwareVersion | minversion | `BackupData` | 🔒 |
| PUT | `upgrade/backup` | `setBackupStatus` | Query:devMacAddr, Query:androidx.core.app.NotificationCompat.CATEGORY_STATUS | minversion | `Void` | 🔒 |
| POST | `upgrade/downgrade` | `getRevertFirmware` | Query:firmwareVersion, Query:fFamily, Query:hardwareVersion, Query:devMacAddr | – | `FirmwareVersion` | 🔒 |
| POST | `upgrade/getUpgrade` | `getFirmwareVersion` | Query:fFamily, Query:firmwareVersion, Query:hardwareVersion | – | `FirmwareVersion` | 📖 |
| POST | `upgrade/updateRecord` | `updateFirmwareVersion` | Query | – | `Void` | 🔒 |

## Advance Automations & alarms (v2)

| Method | Path | App method | Parameters | Headers | Returns | Status |
|---|---|---|---|---|---|---|
| POST | `version=2.0/dev/addAlarms` | `addAlarms` | Query, Query:returnData | minversion | `NetAlarm` | 🔒 |
| POST | `version=2.0/dev/addGroups` | `addGroups` | Query, Query:returnData | minversion | `NetAutomation` | 🔒 |
| POST | `version=2.0/dev/advUpdateBatch` | `updatePortStateForGroup` | Query:devId, Query:devAdvGroupsStr | minversion | `Void` | 🔒 |
| POST | `version=2.0/dev/delAdvbatch` | `delAdvbatch` | Query:devId, Query:groupNums, Query:port | – | `Void` | 🔒 |
| POST | `version=2.0/dev/delAlarmsByid` | `delAlarmsById` | Query | minversion | `Void` | 🔒 |
| POST | `version=2.0/dev/delByid` | `delAdvById` | Query:advId, Query:isDel, Query:isflag | minversion | `Void` | 🔒 |
| POST | `version=2.0/dev/getAlarms` | `getAlarms` | Query:devId | minversion | `List<NetAlarm>` | ✅ |
| POST | `version=2.0/dev/getGroups` | `getGroups` | Query:devId | minversion | `List<NetAutomation>` | ✅ |
| POST | `version=2.0/dev/groupsFromRecipe` | `addGroupsFromRecipe` | Query:devId, Query:devAdvGroupsStr, Query:isResetRecipe, Query:returnData | minversion | `List<NetAutomation>` | 🔒 |
| POST | `version=2.0/dev/home/delAdv` | `delAdvById2` | Query:devId, Query:groupNum, Query:isDel | minversion | `Void` | 🔒 |
| POST | `version=2.0/dev/home/switchAdv` | `switchAdv` | Query:devId, Query:isOn, Query:groupNums | minversion | `Void` | 🔒 |
| POST | `version=2.0/dev/portStateForGroup` | `updatePortStateForGroup` | Query:devId, Query:groupNums, Query:port | – | `Void` | 🔒 |
| GET | `version=2.0/dev/recipe` | `getAdvRecipeList` | Query:advVersion | – | `List<AutomationTemplate>` | ✅ |
| PUT | `version=2.0/dev/restoreAdv` | `restoreAdvGroups` | Field:devAdvGroupsStr | minversion | `List<Object>` | 🔒 |
| PUT | `version=2.0/dev/restoreAlarms` | `restoreAdvAlert` | Field:devAdvAlarmsStr | minversion | `Void` | 🔒 |
| POST | `version=2.0/dev/updateAdvInfo` | `updateAdvInfo` | Query | – | `Void` | 🔒 |
| POST | `version=2.0/dev/updateAlarmsById` | `updateAlarmsById` | Query | minversion | `NetAlarm` | 🔒 |
| POST | `version=2.0/dev/updateChildGroupSort` | `updateChildGroupSort` | Query | minversion | `Void` | 🔒 |
| POST | `version=2.0/dev/updateGroupsById` | `updateGroupsById` | Query | minversion | `NetAutomation` | ✅ (restore) |
| POST | `version=2.0/dev/updateGroupsIsOn` | `updateGroupsIsOn` | Query:advId, Query:isDel, Query:isflag | minversion | `Void` | ✅ |
