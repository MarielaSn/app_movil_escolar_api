from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from rest_framework import permissions, generics
from rest_framework.response import Response
from django.db import transaction
import json

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

        # Filtros según reglas del PDF (Puntos 19 y 20)
        if es_admin:
            # Admin ve todo
            pass
        elif es_maestro:
            # Maestro ve: 'Profesores' y 'Publico General'
            # Como guardamos un string JSON, usamos contains (simple pero funcional para este caso)
            eventos = eventos.filter(
                Q(publico_objetivo__contains='Profesores') | 
                Q(publico_objetivo__contains='Publico General')
            )
        elif es_alumno:
            # Alumno ve: 'Estudiantes' y 'Publico General'
            eventos = eventos.filter(
                Q(publico_objetivo__contains='Estudiantes') | 
                Q(publico_objetivo__contains='Publico General')
            )
        
        # Serializamos
        lista = EventoSerializer(eventos, many=True).data
        
        # Parsear publico_objetivo de string a JSON real para que el frontend lo lea como array
        for evento in lista:
            if "publico_objetivo" in evento and evento["publico_objetivo"]:
                try:
                    evento["publico_objetivo"] = json.loads(evento["publico_objetivo"])
                except:
                    evento["publico_objetivo"] = []

        return Response(lista, 200)

    # Registrar evento (Solo Admin)
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Validar permisos
        if not request.user.groups.filter(name='administrador').exists():
            return Response({"details": "No tienes permisos para registrar eventos"}, 403)

        evento_data = request.data.copy()
        
        # Convertir lista a string JSON si viene como array
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
        
        # Actualizamos campos manual o con serializer partial
        evento.nombre = request.data.get("nombre", evento.nombre)
        evento.tipo = request.data.get("tipo", evento.tipo)
        evento.fecha_realizacion = request.data.get("fecha_realizacion", evento.fecha_realizacion)
        evento.hora_inicio = request.data.get("hora_inicio", evento.hora_inicio)
        evento.hora_fin = request.data.get("hora_fin", evento.hora_fin)
        evento.lugar = request.data.get("lugar", evento.lugar)
        evento.programa_educativo = request.data.get("programa_educativo", evento.programa_educativo)
        evento.descripcion = request.data.get("descripcion", evento.descripcion)
        evento.cupo = request.data.get("cupo", evento.cupo)

        # Tratar JSON y Foreign Key
        if "publico_objetivo" in request.data:
            po = request.data["publico_objetivo"]
            if isinstance(po, list):
                evento.publico_objetivo = json.dumps(po)
            else:
                evento.publico_objetivo = po
        
        if "responsable" in request.data:
            try:
                user_resp = User.objects.get(id=request.data["responsable"])
                evento.responsable = user_resp
            except User.DoesNotExist:
                pass # O lanzar error

        evento.save()
        return Response(EventoSerializer(evento).data, 200)

    # Eliminar evento (Solo Admin)
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='administrador').exists():
            return Response({"details": "No tienes permisos para eliminar"}, 403)

        evento = get_object_or_404(Eventos, id=request.GET.get("id"))
        evento.delete()
        return Response({"details": "Evento eliminado correctamente"}, 200)