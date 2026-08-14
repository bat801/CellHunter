import sys
import json
import os
import torch
from pathlib import Path
import cv2
import pandas as pd
from datetime import datetime
import time

def check_system():
    """Проверяет систему и возвращает информацию о доступных устройствах"""
    info = {
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": None,
        "gpu_memory_gb": None,
        "cpu_count": os.cpu_count(),
        "recommended_device": "cpu"
    }
    
    if info["cuda_available"]:
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["gpu_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / 1024**3
        info["recommended_device"] = "cuda"
    
    return info

def print_system_info():
    """Выводит красивую информацию о системе"""
    info = check_system()
    
    print("\n" + "="*60)
    print("🖥️  СИСТЕМНАЯ ИНФОРМАЦИЯ")
    print("="*60)
    print(f"📊 CPU: {info['cpu_count']} ядер")
    print(f"🔮 CUDA доступна: {'✅ ДА' if info['cuda_available'] else '❌ НЕТ'}")
    
    if info["cuda_available"]:
        print(f"🎮 GPU: {info['gpu_name']}")
        print(f"💾 Видеопамять: {info['gpu_memory_gb']:.1f} ГБ")
        print(f"⚡ Рекомендуемый режим: GPU (будет ~50-100x быстрее)")
    else:
        print("💻 Будет использован CPU (медленнее, но работает на любом компьютере)")
        print("💡 Если у вас есть NVIDIA GPU, установите драйвер и CUDA")
    print("="*60 + "\n")
    
    return info

def get_model(model_name: str = "cellpose", device: str = None):
    """
    Возвращает модель для анализа изображений.
    
    Args:
        model_name: 'yolo' или 'cellpose'
        device: 'cpu' или 'cuda' (если None, выбирается автоматически)
    """
    # Проверяем систему
    sys_info = check_system()
    
    # Если device не указан, используем рекомендуемый
    if device is None:
        device = sys_info["recommended_device"]
    
    # Если выбран GPU, но CUDA недоступна → предупреждение и переключение на CPU
    if device == "cuda" and not sys_info["cuda_available"]:
        print("⚠️  CUDA НЕ ДОСТУПНА! Переключаюсь на CPU...")
        device = "cpu"
    elif device == "cuda" and sys_info["cuda_available"]:
        print(f"✅ Использую GPU: {sys_info['gpu_name']}")
    else:
        print("💻 Использую CPU")
    
    if model_name.lower() == "yolo":
        from ultralytics import YOLO
        model = YOLO("models/yolov8n.pt")
        # YOLO автоматически использует GPU через .to(device)
        return model, device
    
    elif model_name.lower() == "cellpose":
        from cellpose import models
        # CellPose принимает torch.device
        model = models.CellposeModel(
            model_type="nuclei", 
            device=torch.device(device)
        )
        return model, device
    
    else:
        raise ValueError(f"Неизвестная модель: {model_name}")

def process_folder(folder_path: str, model_name: str = "cellpose", device: str = None):
    """
    Обрабатывает все изображения в папке с помощью выбранной модели.
    
    Args:
        folder_path: путь к папке с изображениями
        model_name: 'yolo' или 'cellpose'
        device: 'cpu' или 'cuda'
    """
    # Показываем информацию о системе
    system_info = print_system_info()
    
    # Если device не указан, используем рекомендуемый
    if device is None:
        device = system_info["recommended_device"]
    
    # Проверяем папку
    if not os.path.exists(folder_path):
        print(f"❌ Папка не найдена: {folder_path}")
        return None
    
    # Получаем изображения
    image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
    image_files = [f for f in Path(folder_path).iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"❌ В папке нет изображений: {folder_path}")
        return None
    
    print(f"\n📁 Найдено изображений: {len(image_files)}")
    print(f"📊 Модель: {model_name.upper()}")
    print(f"⚡ Режим: {device.upper()}")
    
    # Загружаем модель
    print(f"\n🔬 Загружаю модель {model_name.upper()}...")
    start_time = time.time()
    try:
        model, actual_device = get_model(model_name, device)
        print(f"✅ Модель загружена за {time.time() - start_time:.1f} сек.")
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return None
    
    results = []
    total = len(image_files)
    
    print("\n🔄 Начинаю обработку...\n")
    
    for idx, img_path in enumerate(image_files, 1):
        print(f"PROGRESS:{idx}/{total}:{img_path.name}")
        
        # Читаем изображение
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"⚠️ Не удалось прочитать: {img_path.name}")
            continue
        
        # Замеряем время обработки
        img_start = time.time()
        
        # Обработка в зависимости от модели
        try:
            if model_name.lower() == "yolo":
                # Для YOLO нужно RGB
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
                elif img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                result = model(img)
                count = len(result[0].boxes)
                
            else:  # cellpose
                # Для CellPose нужен grayscale
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                masks, flows, styles = model.eval(
                    img, 
                    diameter=None, 
                    channels=[0, 0],
                    do_3D=False
                )
                count = int(masks.max())
        except Exception as e:
            print(f"❌ Ошибка обработки {img_path.name}: {e}")
            continue
        
        img_time = time.time() - img_start
        
        # Сохраняем результат
        results.append({
            'filename': img_path.name,
            'count': count,
            'width': img.shape[1],
            'height': img.shape[0],
            'model': model_name,
            'device': actual_device,
            'time_seconds': round(img_time, 2)
        })
        
        # Прогресс с временем
        elapsed = time.time() - start_time
        avg_time = elapsed / idx
        remaining = avg_time * (total - idx)
        print(f"   ✅ Найдено: {count} объектов | ⏱️ {img_time:.1f} сек | Осталось: ~{remaining:.1f} сек")
    
    if not results:
        print("❌ Не удалось обработать ни одного изображения")
        return None
    
    # Сохраняем в Excel
    df = pd.DataFrame(results)
    excel_path = Path(folder_path) / f"cellhunter_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(excel_path, index=False)
    
    total_time = time.time() - start_time
    
    output = {
        "status": "success",
        "total_files": total,
        "processed_files": len(results),
        "excel_path": str(excel_path),
        "model": model_name,
        "device": actual_device,
        "total_time_seconds": round(total_time, 2),
        "results": results
    }
    
    print(f"\n{'='*60}")
    print(f"✅ АНАЛИЗ ЗАВЕРШЕН!")
    print(f"📊 Обработано: {len(results)}/{total} изображений")
    print(f"⏱️ Общее время: {total_time:.1f} сек.")
    print(f"📁 Отчет: {excel_path}")
    print(f"{'='*60}\n")
    
    print(json.dumps(output))
    return output

if __name__ == "__main__":
    # Парсим аргументы командной строки
    args = sys.argv
    
    folder = None
    model_name = "cellpose"
    device = None  # None = автоопределение
    
    for i, arg in enumerate(args):
        if arg in ["--model", "-m"] and i+1 < len(args):
            model_name = args[i+1].lower()
        elif arg in ["--device", "-d"] and i+1 < len(args):
            device = args[i+1].lower()
        elif arg in ["--cpu"]:
            device = "cpu"
        elif arg in ["--gpu"]:
            device = "cuda"
        elif not arg.startswith("-") and i > 0:
            if folder is None:
                folder = arg
    
    if folder is None:
        print("\n" + "="*60)
        print("🔬 CellHunter - Анализатор клеточных изображений")
        print("="*60)
        print("\nИспользование:")
        print("  python -m analyzer.main <путь_к_папке> [опции]")
        print("\nОпции:")
        print("  --model, -m   yolo или cellpose (по умолчанию: cellpose)")
        print("  --device, -d  cpu или cuda (по умолчанию: автоопределение)")
        print("  --cpu         принудительно использовать CPU")
        print("  --gpu         принудительно использовать GPU")
        print("\nПримеры:")
        print("  python -m analyzer.main images/ --model cellpose --gpu")
        print("  python -m analyzer.main images/ --model yolo --cpu")
        print("="*60 + "\n")
        sys.exit(1)
    
    print(f"🚀 Запуск анализа папки: {folder}")
    process_folder(folder, model_name, device)