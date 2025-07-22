# Third Party Imports
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from rest_framework import status
from django.utils.dateparse import parse_date

#Local Imports
from devices.models import (
    Device,
    DeviceData
)
from devices.pagination import DeviceDataPagination
from devices.serializers import (
    DeviceDataSerializer, 
    DeviceSerializer
)

class DeviceAPIView(APIView):
    
    def get(self, request): #Working -> #default  -> #replica
        devices = Device.objects.all()
        device_id = request.query_params.get("device_id")
        device_type = request.query_params.get("device_type")
        device_type_name = request.query_params.get("device_type_name")
        is_connected = request.query_params.get("is_connected")
        last_seen = request.query_params.get("last_seen")

        if device_id:
            devices = devices.filter(device_id__icontains=device_id)

        if device_type:
            devices = devices.filter(device_type__icontains=device_type)

        if device_type_name:
            devices = devices.filter(device_type_name__icontains=device_type_name)

        if is_connected is not None:
            devices = devices.filter(is_connected=is_connected.lower() == 'true')

        if last_seen:
            try:
                parsed_date = parse_date(last_seen)
                if parsed_date:
                    devices = devices.filter(last_seen__date=parsed_date)
            except:
                pass

        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = {
            'device_id': request.data.get('device_id'),
            'device_type': request.data.get('device_type'),
            'device_type_name': request.data.get('device_type_name'),
        }
        serializer = DeviceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_object(self, pk):
        try:
            return Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return None

    def put(self, request, pk):
        device = self.get_object(pk)
        if not device:
            return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'device_type': request.data.get('device_type', device.device_type),
            'device_type_name': request.data.get('device_type_name', device.device_type_name),
            'is_connected': request.data.get('is_connected', device.is_connected),
        }

        serializer = DeviceSerializer(device, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        device = self.get_object(pk)
        if not device:
            return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DeviceDataListView(APIView):
    def get(self, request):
        queryset = DeviceData.objects.all()

        # Filters
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')
        vendor_id = request.GET.get('vendor_id')
        imei = request.GET.get('imei')

        if start_time and end_time:
            try:
                queryset = queryset.filter(timestamp__range=(parse_datetime(start_time), parse_datetime(end_time)))
            except Exception:
                return Response({"error": "Invalid datetime format. Use ISO 8601."}, status=400)

        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)

        if imei:
            queryset = queryset.filter(IMEI=imei)

        paginator = DeviceDataPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = DeviceDataSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    