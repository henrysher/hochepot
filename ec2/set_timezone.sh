#!/bin/bash
# Utility to configure instance timezone on AWS
# 2014/04/24

timezone() {
    case $1 in
        'us-east-1') echo "US/Eastern";;
        'us-west-2') echo "US/Pacific";;
        'ap-northeast-1') echo "Asia/Tokyo";;
        'ap-sortheast-1') echo "Asia/Singapore";;
        'ap-sortheast-2') echo "Australia/Sydney";;
        'sa-east-1') echo "America/Sao_Paulo";;
        'eu-west-1') echo "Europe/Dublin";;
        *) return 255;;
    esac
}

LOG="SET_TIMEZONE"

REGION_URL="http://169.254.169.254/latest/meta-data/placement/availability-zone"
AZ_ID=`curl --retry 3 --retry-delay 0 --silent --fail ${REGION_URL}`
if [ $? -ne 0 ] ; then
   echo "Unable to retrive Region Name from meta-data. " | logger -t "${LOG}"
   exit 1
else
   REGION=${AZ_ID:0:${#AZ_ID} - 1}
   echo "Retrived the Region Name: ${REGION} from meta-data" | logger -t "${LOG}"
fi

TIMEZONE=$( timezone ${REGION} )
if [[ $? -ne 255 ]]; then
   echo "Find the correct timezone: '${TIMEZONE}' for '${REGION}'" | logger -t "${LOG}"
else
   echo "Unable to retrive correct TIMEZONE for '${REGION}': keep current" | logger -t "${LOG}"
   exit 1
fi

CLOCKFILE="/etc/sysconfig/clock"
ESCAPED_TIMEZONE=${TIMEZONE//\//\\\/}
if grep -Fxq "ZONE=\"${TIMEZONE}\"" ${CLOCKFILE}
  then
  echo "No need to update '${CLOCKFILE}': already exists" | logger -t "${LOG}"
else
  sudo sed -i "s/ZONE=.*/ZONE=\"${ESCAPED_TIMEZONE}\"/" ${CLOCKFILE}
  if ! grep -Fxq "ZONE=\"${TIMEZONE}\"" ${CLOCKFILE}
    then 
    echo "Unable to update '${CLOCKFILE}'" | logger -t "${LOG}"
    exit 1
  fi
fi

TIMEFILE="/etc/localtime"
if diff -q /usr/share/zoneinfo/${TIMEZONE} ${TIMEFILE}
  then
  echo "No need to update '${TIMEFILE}': already exists" | logger -t "${LOG}"
  exit 0
fi
sudo ln -fs /usr/share/zoneinfo/${TIMEZONE} ${TIMEFILE}
if diff -q /usr/share/zoneinfo/${TIMEZONE} ${TIMEFILE}
  then
  echo "==> success" | logger -t "${LOG}"
  exit 0
else
  echo "Unable to update '${TIMEFILE}'" | logger -t "${LOG}"
  exit 1
fi
