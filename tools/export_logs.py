#!/usr/bin/env python3
"""Utilidad para exportar registros de acceso."""
import sys
import csv
from pathlib import Path
from datetime import UTC, datetime, timedelta
import json

# CORREGIDO: Manejo robusto de imports
try:
    from core.database import get_session, AccessLog, User
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from core.database import get_session, AccessLog, User

def export_logs(days_back=30, output_file=None, format='csv'):
    """
    Exportar registros de acceso a CSV o JSON
    
    Args:
        days_back: Número de días hacia atrás para exportar
        output_file: Nombre del archivo de salida (opcional)
        format: Formato de exportación ('csv' o 'json')
    """
    session = get_session()
    
    try:
        # Calcular fecha de inicio
        start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_back)
        
        # Consultar registros
        logs = session.query(AccessLog, User)\
            .join(User, User.uuid == AccessLog.user_uuid)\
            .filter(AccessLog.timestamp >= start_date)\
            .order_by(AccessLog.timestamp.desc())\
            .all()
        
        if not logs:
            print(f"No se encontraron registros en los últimos {days_back} días")
            return None
        
        # Generar nombre de archivo si no se especificó
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = 'json' if format == 'json' else 'csv'
            output_file = f"access_logs_{timestamp}.{extension}"
        
        # Asegurar que el archivo tenga la extensión correcta
        output_path = Path(output_file)
        if format == 'json' and output_path.suffix != '.json':
            output_path = output_path.with_suffix('.json')
        elif format == 'csv' and output_path.suffix != '.csv':
            output_path = output_path.with_suffix('.csv')
        
        if format == 'json':
            export_to_json(logs, output_path)
        else:
            export_to_csv(logs, output_path)
        
        print(f"✓ Exportados {len(logs)} registros a: {output_path}")
        
        # Mostrar resumen
        show_summary(logs)
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error exportando registros: {e}")
        return None
    finally:
        session.close()

def export_to_csv(logs, output_file):
    """Exportar registros a CSV"""
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:  # utf-8-sig para Excel
        fieldnames = ['ID', 'Usuario', 'Email', 'Tipo', 'Fecha', 'Hora', 'Día Semana']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for log, user in logs:
            writer.writerow({
                'ID': log.id,
                'Usuario': user.name,
                'Email': user.email,
                'Tipo': log.access_type.upper(),
                'Fecha': log.timestamp.strftime('%Y-%m-%d'),
                'Hora': log.timestamp.strftime('%H:%M:%S'),
                'Día Semana': get_weekday_spanish(log.timestamp.weekday())
            })

def export_to_json(logs, output_file):
    """Exportar registros a JSON"""
    data = {
        'export_date': datetime.now().isoformat(),
        'total_records': len(logs),
        'records': []
    }
    
    for log, user in logs:
        data['records'].append({
            'id': log.id,
            'user': {
                'uuid': user.uuid,
                'name': user.name,
                'email': user.email,
                'is_active': user.is_active
            },
            'access': {
                'type': log.access_type,
                'timestamp': log.timestamp.isoformat(),
                'date': log.timestamp.strftime('%Y-%m-%d'),
                'time': log.timestamp.strftime('%H:%M:%S'),
                'weekday': log.timestamp.strftime('%A')
            }
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_weekday_spanish(weekday):
    """Obtener día de la semana en español"""
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    return days[weekday]

def show_summary(logs):
    """Mostrar resumen de los registros exportados"""
    entries = sum(1 for log, _ in logs if log.access_type == "entry")
    exits = sum(1 for log, _ in logs if log.access_type == "exit")
    
    print(f"\n📊 Resumen:")
    print(f"  - Entradas: {entries}")
    print(f"  - Salidas: {exits}")
    print(f"  - Total: {len(logs)}")
    
    # Usuarios únicos
    unique_users = set(user.name for _, user in logs)
    print(f"  - Usuarios únicos: {len(unique_users)}")
    
    # Usuario más activo
    from collections import Counter
    user_counts = Counter(user.name for _, user in logs)
    if user_counts:
        most_active = user_counts.most_common(1)[0]
        print(f"  - Usuario más activo: {most_active[0]} ({most_active[1]} accesos)")
    
    # Día con más actividad
    day_counts = Counter(log.timestamp.date() for log, _ in logs)
    if day_counts:
        busiest_day = day_counts.most_common(1)[0]
        print(f"  - Día más activo: {busiest_day[0]} ({busiest_day[1]} accesos)")
    
    # Hora pico
    hour_counts = Counter(log.timestamp.hour for log, _ in logs)
    if hour_counts:
        peak_hour = hour_counts.most_common(1)[0]
        print(f"  - Hora pico: {peak_hour[0]}:00-{peak_hour[0]}:59 ({peak_hour[1]} accesos)")

def export_user_report(user_email, output_file=None):
    """
    Exportar reporte de un usuario específico
    
    Args:
        user_email: Email del usuario
        output_file: Archivo de salida (opcional)
    """
    session = get_session()
    
    try:
        # Buscar usuario
        user = session.query(User).filter_by(email=user_email).first()
        if not user:
            print(f"❌ Usuario no encontrado: {user_email}")
            return None
        
        # Obtener todos los registros del usuario
        logs = session.query(AccessLog)\
            .filter_by(user_uuid=user.uuid)\
            .order_by(AccessLog.timestamp.desc())\
            .all()
        
        if not logs:
            print(f"No hay registros para {user.name}")
            return None
        
        # Generar nombre de archivo
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = user.name.replace(" ", "_").lower()
            output_file = f"report_{safe_name}_{timestamp}.csv"
        
        # Escribir reporte
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            # Escribir información del usuario
            csvfile.write(f"REPORTE DE USUARIO\n")
            csvfile.write(f"==================\n")
            csvfile.write(f"Nombre: {user.name}\n")
            csvfile.write(f"Email: {user.email}\n")
            csvfile.write(f"Estado: {'Activo' if user.is_active else 'Inactivo'}\n")
            csvfile.write(f"Registrado: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            csvfile.write(f"Total de accesos: {len(logs)}\n")
            csvfile.write(f"\n")
            
            # Escribir registros
            fieldnames = ['ID', 'Tipo', 'Fecha', 'Hora', 'Día']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for log in logs:
                writer.writerow({
                    'ID': log.id,
                    'Tipo': log.access_type.upper(),
                    'Fecha': log.timestamp.strftime('%Y-%m-%d'),
                    'Hora': log.timestamp.strftime('%H:%M:%S'),
                    'Día': get_weekday_spanish(log.timestamp.weekday())
                })
        
        print(f"✓ Reporte generado: {output_file}")
        
        # Mostrar estadísticas
        entries = sum(1 for log in logs if log.access_type == "entry")
        exits = sum(1 for log in logs if log.access_type == "exit")
        
        print(f"\n📊 Estadísticas de {user.name}:")
        print(f"  - Entradas: {entries}")
        print(f"  - Salidas: {exits}")
        
        if logs:
            first_access = logs[-1].timestamp
            last_access = logs[0].timestamp
            days_active = (last_access - first_access).days + 1
            
            print(f"  - Primer acceso: {first_access.strftime('%Y-%m-%d %H:%M')}")
            print(f"  - Último acceso: {last_access.strftime('%Y-%m-%d %H:%M')}")
            print(f"  - Días activo: {days_active}")
            
            if days_active > 0:
                avg_daily = len(logs) / days_active
                print(f"  - Promedio diario: {avg_daily:.1f} accesos")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error generando reporte: {e}")
        return None
    finally:
        session.close()

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Exportar registros de acceso")
    
    parser.add_argument(
        '-d', '--days',
        type=int,
        default=30,
        help='Número de días hacia atrás para exportar (default: 30)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Archivo de salida'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['csv', 'json'],
        default='csv',
        help='Formato de exportación (default: csv)'
    )
    parser.add_argument(
        '--today',
        action='store_true',
        help='Exportar solo registros de hoy'
    )
    parser.add_argument(
        '--week',
        action='store_true',
        help='Exportar registros de la última semana'
    )
    parser.add_argument(
        '--month',
        action='store_true',
        help='Exportar registros del último mes'
    )
    parser.add_argument(
        '--user',
        type=str,
        help='Generar reporte de un usuario específico (email)'
    )
    
    args = parser.parse_args()
    
    # Si se especifica un usuario, generar reporte individual
    if args.user:
        export_user_report(args.user, args.output)
        return
    
    # Ajustar días según flags
    if args.today:
        days = 1
    elif args.week:
        days = 7
    elif args.month:
        days = 30
    else:
        days = args.days
    
    export_logs(days_back=days, output_file=args.output, format=args.format)

if __name__ == "__main__":
    main()
