from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from rest_framework import permissions, generics
from rest_framework.response import Response
from django.db import transaction
import json

# Asegúrate de importar el nombre correcto
from control_escolar_desit_api.serializers import EventoSerializer
from control_escolar_desit_api.models import Eventos, User

class EventosAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        # Obtener el rol del usuario logueado
        user_groups = request.user.groups.values_list('name', flat=True)
        es_admin = 'administrador' in user_groups
        es_maestro = 'maestro' in user_groups
        es_alumno = 'alumno' in user_groups

        # Query base: ordenados por fecha
        eventos = Eventos.objects.all().order_by("fecha_realizacion")

        # Filtros según reglas
        if es_admin:
            pass
        elif es_maestro:
            eventos = eventos.filter(
                Q(publico_objetivo__contains='Profesores') | 
                Q(publico_objetivo__contains='Publico General') |
                Q(publico_objetivo__contains='Público General') # Agregado por si acaso
            )
        elif es_alumno:
            eventos = eventos.filter(
                Q(publico_objetivo__contains='Estudiantes') | 
                Q(publico_objetivo__contains='Publico General') |
                Q(publico_objetivo__contains='Público General')
            )
        
        # Serializamos
        lista = EventoSerializer(eventos, many=True).data
        
        # Parsear publico_objetivo de string a JSON para el frontend
        for evento in lista:
            # Agregamos un campo helper para mostrar el nombre facil en la tabla
            if "responsable_data" in evento:
                 evento["responsable_nombre"] = f"{evento['responsable_data']['first_name']} {evento['responsable_data']['last_name']}"

            if "publico_objetivo" in evento and evento["publico_objetivo"]:
                try:
                    evento["publico_objetivo"] = json.loads(evento["publico_objetivo"])
                except:
                    evento["publico_objetivo"] = []

        return Response(lista, 200)

    # Registrar evento (Solo Admin)
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='administrador').exists():
            return Response({"details": "No tienes permisos para registrar eventos"}, 403)

        evento_data = request.data.copy()
        
        # Convertir lista a string JSON si viene como array desde Angular
        if 'publico_objetivo' in evento_data:
            if isinstance(evento_data['publico_objetivo'], list):
                evento_data['publico_objetivo'] = json.dumps(evento_data['publico_objetivo'])

        serializer = EventoSerializer(data=evento_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, 201)
        
        return Response(serializer.errors, 400)

class EventosView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    # Obtener un evento por ID
    def get(self, request, *args, **kwargs):
        evento = get_object_or_404(Eventos, id=request.GET.get("id"))
        data = EventoSerializer(evento).data
        
        # Parsear JSON
        try:
            data["publico_objetivo"] = json.loads(data["publico_objetivo"])
        except:
            pass
            
        return Response(data, 200)

    # Actualizar evento (Solo Admin)
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='administrador').exists():
            return Response({"details": "No tienes permisos para editar"}, 403)

        evento = get_object_or_404(Eventos, id=request.data.get("id"))
        data_update = request.data.copy()

        # Tratar JSON de publico_objetivo antes de pasar al serializer
        if "publico_objetivo" in data_update:
            po = data_update["publico_objetivo"]
            if isinstance(po, list):
                data_update["publico_objetivo"] = json.dumps(po)
        
        # Usamos partial=True para actualizar solo los campos que vengan
        serializer = EventoSerializer(evento, data=data_update, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, 200)
        
        return Response(serializer.errors, 400)

    # Eliminar evento (Solo Admin)
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='administrador').exists():
            return Response({"details": "No tienes permisos para eliminar"}, 403)

        evento = get_object_or_404(Eventos, id=request.GET.get("id"))
        evento.delete()
        return Response({"details": "Evento eliminado correctamente"}, 200)