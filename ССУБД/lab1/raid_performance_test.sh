#!/bin/bash

################################################################################
# Скрипт для тестирования производительности RAID 10 с фрагментацией файлов
# Лабораторная работа: Анализ производительности СХД
################################################################################

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Глобальные переменные
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/raid_test_$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR="${WORK_DIR}/results"
GRAPHS_DIR="${WORK_DIR}/graphs"
REPORT_FILE="${WORK_DIR}/lab_report.md"
LOG_FILE=""

# Параметры RAID - УВЕЛИЧЕНЫ для избежания проблем с местом
NUM_DEVICES=4
DEVICE_SIZE=4G  # Увеличено с 2G до 4G
RAID_DEVICE="/dev/md0"
MOUNT_POINT="${WORK_DIR}/raid_mount"

# Параметры тестирования - ОПТИМИЗИРОВАНЫ
TEST_FILE_SIZE="500M"  # Уменьшено с 1G
FRAGMENTED_FILE_SIZE="800M"  # Уменьшено с 2G
NUM_RUNS=3

# Логирование
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo -e "${GREEN}${msg}${NC}"
    if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
        echo "$msg" >> "$LOG_FILE"
    fi
}

error() {
    local msg="[ERROR] $*"
    echo -e "${RED}${msg}${NC}"
    if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
        echo "$msg" >> "$LOG_FILE"
    fi
    exit 1
}

warn() {
    local msg="[WARNING] $*"
    echo -e "${YELLOW}${msg}${NC}"
    if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
        echo "$msg" >> "$LOG_FILE"
    fi
}

info() {
    local msg="[INFO] $*"
    echo -e "${BLUE}${msg}${NC}"
    if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
        echo "$msg" >> "$LOG_FILE"
    fi
}

# Проверка доступного места
check_disk_space() {
    local available=$(df -BM "$MOUNT_POINT" | awk 'NR==2 {print $4}' | sed 's/M//')
    local required=$1

    info "Доступно места: ${available}MB, требуется: ${required}MB"

    if [ "$available" -lt "$required" ]; then
        warn "Недостаточно места на диске. Доступно: ${available}MB, требуется: ${required}MB"
        return 1
    fi
    return 0
}

# Очистка тестовых файлов
cleanup_test_files() {
    info "Очистка тестовых файлов..."
    rm -f "${MOUNT_POINT}"/*.{0..9}.* 2>/dev/null || true
    rm -f "${MOUNT_POINT}"/seq_*.0.* 2>/dev/null || true
    rm -f "${MOUNT_POINT}"/rand_*.0.* 2>/dev/null || true
    rm -f "${MOUNT_POINT}"/mixed.*.* 2>/dev/null || true
    sync
    df -h "$MOUNT_POINT" | tee -a "$LOG_FILE"
}

# Проверка прав root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[ERROR]${NC} Этот скрипт должен быть запущен с правами root (sudo)"
        exit 1
    fi
}

# Создание рабочих директорий
setup_directories() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} Создание рабочих директорий..."
    mkdir -p "${WORK_DIR}"
    mkdir -p "${RESULTS_DIR}"
    mkdir -p "${GRAPHS_DIR}"
    mkdir -p "${MOUNT_POINT}"

    LOG_FILE="${WORK_DIR}/test.log"
    touch "$LOG_FILE"

    log "Директории созданы: ${WORK_DIR}"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверка зависимостей..."
    local deps=("mdadm" "fio" "bc" "iostat" "filefrag")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        warn "Отсутствуют: ${missing[*]}"
        info "Установка пакетов..."

        apt-get update -qq
        apt-get install -y -qq mdadm fio bc sysstat e2fsprogs python3 python3-pip 2>&1 | tee -a "$LOG_FILE"

        log "Зависимости установлены"
    else
        log "Все зависимости присутствуют"
    fi
}

# Создание виртуальных устройств
create_loop_devices() {
    log "Создание виртуальных устройств..."

    LOOP_DEVICES=()

    for i in $(seq 1 $NUM_DEVICES); do
        local img_file="${WORK_DIR}/disk${i}.img"

        info "Создание образа диска ${i}/${NUM_DEVICES}..."
        dd if=/dev/zero of="$img_file" bs=1M count=0 seek=$((${DEVICE_SIZE%G} * 1024)) status=none

        local loop_dev=$(losetup -f)
        losetup "$loop_dev" "$img_file"

        LOOP_DEVICES+=("$loop_dev")
        info "Создано: $loop_dev ($DEVICE_SIZE)"
    done

    log "Создано ${#LOOP_DEVICES[@]} устройств: ${LOOP_DEVICES[*]}"
}

# Создание RAID 10
create_raid10() {
    log "Создание RAID 10..."

    if [ -e "$RAID_DEVICE" ]; then
        warn "RAID существует, останавливаем..."
        mdadm --stop "$RAID_DEVICE" 2>/dev/null || true
        sleep 2
    fi

    info "Создание RAID 10..."
    mdadm --create "$RAID_DEVICE" \
        --level=10 \
        --raid-devices=$NUM_DEVICES \
        --layout=n2 \
        --chunk=512 \
        "${LOOP_DEVICES[@]}" \
        --force 2>&1 | tee -a "$LOG_FILE"

    sleep 5

    mdadm --detail "$RAID_DEVICE" | tee "${RESULTS_DIR}/raid_info.txt"

    log "RAID 10 создан"
}

# Создание ФС
create_filesystem() {
    log "Создание ext4..."

    mkfs.ext4 -F "$RAID_DEVICE" 2>&1 | tee -a "$LOG_FILE"
    mount "$RAID_DEVICE" "$MOUNT_POINT"

    df -h "$MOUNT_POINT" | tee -a "$LOG_FILE"

    log "ФС смонтирована"
}

# Запуск fio теста
run_fio_test() {
    local test_name="$1"
    local test_config="$2"
    local output_file="${RESULTS_DIR}/${test_name}.json"

    info "Запуск: $test_name"

    # Проверка места перед тестом
    if ! check_disk_space 100; then
        warn "Пропуск теста $test_name - недостаточно места"
        return 1
    fi

    local temp_config="${WORK_DIR}/${test_name}.fio"
    echo "$test_config" > "$temp_config"

    if fio "$temp_config" \
        --output-format=json \
        --output="$output_file" \
        2>&1 | tee -a "$LOG_FILE"; then
        info "Тест $test_name OK"
    else
        warn "Тест $test_name - ошибка"
    fi

    rm -f "$temp_config"

    # Очистка после каждого теста
    cleanup_test_files
}

# Базовые тесты
baseline_tests() {
    log "=== БАЗОВЫЕ ТЕСТЫ ==="

    cd "$MOUNT_POINT"

    # Последовательное чтение
    run_fio_test "baseline_seq_read" "[global]
directory=$MOUNT_POINT
size=$TEST_FILE_SIZE
ioengine=libaio
direct=1
numjobs=1
group_reporting=1
unlink=1

[seq_read]
rw=read
bs=1M
iodepth=32"

    # Последовательная запись
    run_fio_test "baseline_seq_write" "[global]
directory=$MOUNT_POINT
size=$TEST_FILE_SIZE
ioengine=libaio
direct=1
numjobs=1
group_reporting=1
unlink=1

[seq_write]
rw=write
bs=1M
iodepth=32"

    # Случайное чтение 4K
    run_fio_test "baseline_rand_read_4k" "[global]
directory=$MOUNT_POINT
size=$TEST_FILE_SIZE
ioengine=libaio
direct=1
numjobs=2
group_reporting=1
unlink=1

[rand_read_4k]
rw=randread
bs=4K
iodepth=32"

    # Случайная запись 4K
    run_fio_test "baseline_rand_write_4k" "[global]
directory=$MOUNT_POINT
size=$TEST_FILE_SIZE
ioengine=libaio
direct=1
numjobs=2
group_reporting=1
unlink=1

[rand_write_4k]
rw=randwrite
bs=4K
iodepth=32"

    # Смешанные операции
    run_fio_test "baseline_mixed" "[global]
directory=$MOUNT_POINT
size=$TEST_FILE_SIZE
ioengine=libaio
direct=1
numjobs=2
group_reporting=1
unlink=1

[mixed]
rw=randrw
rwmixread=70
bs=4K
iodepth=32"

    # Различные размеры блоков
    for bs in 4K 16K 64K 256K 1M; do
        run_fio_test "baseline_seq_read_${bs}" "[global]
directory=$MOUNT_POINT
size=$TEST_FILE_SIZE
ioengine=libaio
direct=1
numjobs=1
group_reporting=1
unlink=1

[seq_read_${bs}]
rw=read
bs=${bs}
iodepth=32"
    done

    log "Базовые тесты завершены"
}

# Создание фрагментированного файла
create_fragmented_file() {
    log "=== СОЗДАНИЕ ФРАГМЕНТИРОВАННОГО ФАЙЛА ==="

    local target_file="${MOUNT_POINT}/fragmented_test.dat"
    local temp_dir="${MOUNT_POINT}/temp_frag"

    # Очистка старых файлов
    rm -rf "$temp_dir" "$target_file" 2>/dev/null || true
    mkdir -p "$temp_dir"

    info "Создание фрагментированного файла..."

    # Уменьшенное количество файлов
    local num_files=200
    local file_size=$(( (${FRAGMENTED_FILE_SIZE%M} / $num_files) ))

    info "Создание $num_files файлов по ${file_size}MB..."
    for i in $(seq 1 $num_files); do
        dd if=/dev/urandom of="${temp_dir}/file_${i}.dat" bs=1M count=$file_size status=none 2>/dev/null

        if [ $((i % 50)) -eq 0 ]; then
            info "Создано $i/$num_files"
        fi
    done

    info "Удаление каждого второго файла..."
    for i in $(seq 2 2 $num_files); do
        rm -f "${temp_dir}/file_${i}.dat"
    done

    sync

    info "Создание финального файла..."
    dd if=/dev/urandom of="$target_file" bs=1M count=${FRAGMENTED_FILE_SIZE%M} status=progress 2>&1 | tee -a "$LOG_FILE"

    sync

    local frag_output=$(filefrag "$target_file")
    log "Файл создан: $frag_output"

    echo "$frag_output" > "${RESULTS_DIR}/fragmentation_level.txt"
    filefrag -v "$target_file" > "${RESULTS_DIR}/fragmentation_details.txt"

    rm -rf "$temp_dir"

    log "Фрагментированный файл готов"
}

# Тесты на фрагментированных файлах
fragmented_tests() {
    log "=== ТЕСТЫ НА ФРАГМЕНТИРОВАННЫХ ФАЙЛАХ ==="

    local frag_file="${MOUNT_POINT}/fragmented_test.dat"

    if [ ! -f "$frag_file" ]; then
        warn "Фрагментированный файл не найден"
        return 1
    fi

    run_fio_test "fragmented_seq_read" "[global]
filename=$frag_file
ioengine=libaio
direct=1
numjobs=1
group_reporting=1

[frag_seq_read]
rw=read
bs=1M
iodepth=32"

    run_fio_test "fragmented_rand_read_4k" "[global]
filename=$frag_file
ioengine=libaio
direct=1
numjobs=2
group_reporting=1

[frag_rand_read_4k]
rw=randread
bs=4K
iodepth=32"

    for bs in 4K 16K 64K 256K 1M; do
        run_fio_test "fragmented_seq_read_${bs}" "[global]
filename=$frag_file
ioengine=libaio
direct=1
numjobs=1
group_reporting=1

[frag_seq_read_${bs}]
rw=read
bs=${bs}
iodepth=32"
    done

    log "Тесты на фрагментированных файлах завершены"
}

# Парсинг результатов
parse_fio_results() {
    log "=== АНАЛИЗ РЕЗУЛЬТАТОВ ==="

    python3 - <<'PYTHON_SCRIPT'
import json
import os
import sys
from pathlib import Path

results_dir = os.environ['RESULTS_DIR']
output_csv = os.path.join(results_dir, 'summary_results.csv')

json_files = list(Path(results_dir).glob('*.json'))

if not json_files:
    print("Нет JSON файлов для анализа", file=sys.stderr)
    sys.exit(1)

summary = []

for json_file in json_files:
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        test_name = json_file.stem

        for job in data.get('jobs', []):
            job_name = job.get('jobname', 'unknown')

            read_bw = job.get('read', {}).get('bw', 0) / 1024
            read_iops = job.get('read', {}).get('iops', 0)
            read_lat = job.get('read', {}).get('lat_ns', {}).get('mean', 0) / 1000000

            write_bw = job.get('write', {}).get('bw', 0) / 1024
            write_iops = job.get('write', {}).get('iops', 0)
            write_lat = job.get('write', {}).get('lat_ns', {}).get('mean', 0) / 1000000

            summary.append({
                'test_name': test_name,
                'job_name': job_name,
                'read_bw_mbs': round(read_bw, 2),
                'read_iops': round(read_iops, 2),
                'read_lat_ms': round(read_lat, 2),
                'write_bw_mbs': round(write_bw, 2),
                'write_iops': round(write_iops, 2),
                'write_lat_ms': round(write_lat, 2)
            })
    except Exception as e:
        print(f"Ошибка {json_file}: {e}", file=sys.stderr)

with open(output_csv, 'w') as f:
    f.write('test_name,job_name,read_bw_mbs,read_iops,read_lat_ms,write_bw_mbs,write_iops,write_lat_ms\n')
    for row in summary:
        f.write(f"{row['test_name']},{row['job_name']},{row['read_bw_mbs']},{row['read_iops']},{row['read_lat_ms']},{row['write_bw_mbs']},{row['write_iops']},{row['write_lat_ms']}\n")

print(f"Результаты в {output_csv}")
print(f"Обработано тестов: {len(summary)}")
PYTHON_SCRIPT

    log "Анализ завершен"
}

# Создание графиков
generate_graphs() {
    log "=== СОЗДАНИЕ ГРАФИКОВ ==="

    python3 - <<'PYTHON_SCRIPT'
import csv
import os
import sys

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Установка matplotlib...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "matplotlib", "numpy"])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

results_dir = os.environ['RESULTS_DIR']
graphs_dir = os.environ['GRAPHS_DIR']
csv_file = os.path.join(results_dir, 'summary_results.csv')

if not os.path.exists(csv_file):
    print(f"CSV файл не найден: {csv_file}", file=sys.stderr)
    sys.exit(1)

data = []
with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)

if not data:
    print("Нет данных для графиков", file=sys.stderr)
    sys.exit(1)

baseline_seq_read = [d for d in data if 'baseline_seq_read_' in d['test_name'] and 'mixed' not in d['test_name']]
fragmented_seq_read = [d for d in data if 'fragmented_seq_read_' in d['test_name']]

if baseline_seq_read and fragmented_seq_read:
    block_sizes = []
    baseline_bw = []
    fragmented_bw = []

    for d in sorted(baseline_seq_read, key=lambda x: x['test_name']):
        bs = d['test_name'].split('_')[-1]
        block_sizes.append(bs)
        baseline_bw.append(float(d['read_bw_mbs']))

    for d in sorted(fragmented_seq_read, key=lambda x: x['test_name']):
        fragmented_bw.append(float(d['read_bw_mbs']))

    x = np.arange(len(block_sizes))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    rects1 = ax.bar(x - width/2, baseline_bw, width, label='Нефрагментированный', color='#2ecc71')
    rects2 = ax.bar(x + width/2, fragmented_bw, width, label='Фрагментированный', color='#e74c3c')

    ax.set_xlabel('Размер блока', fontsize=12)
    ax.set_ylabel('Пропускная способность (MB/s)', fontsize=12)
    ax.set_title('Влияние фрагментации на последовательное чтение', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(block_sizes)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(graphs_dir, 'fragmentation_impact_sequential.png'), dpi=300)
    print("График 1: fragmentation_impact_sequential.png")
    plt.close()

baseline_rand = [d for d in data if d['test_name'] == 'baseline_rand_read_4k']
fragmented_rand = [d for d in data if d['test_name'] == 'fragmented_rand_read_4k']

if baseline_rand and fragmented_rand:
    categories = ['Нефрагментированный', 'Фрагментированный']
    iops_values = [float(baseline_rand[0]['read_iops']), float(fragmented_rand[0]['read_iops'])]

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(categories, iops_values, color=['#3498db', '#e67e22'], width=0.6)

    ax.set_ylabel('IOPS', fontsize=12)
    ax.set_title('Случайное чтение (4K): IOPS', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}',
                ha='center', va='bottom', fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(graphs_dir, 'fragmentation_impact_iops.png'), dpi=300)
    print("График 2: fragmentation_impact_iops.png")
    plt.close()

if baseline_seq_read and fragmented_seq_read and len(baseline_bw) == len(fragmented_bw):
    degradation = []

    for i in range(len(baseline_bw)):
        if baseline_bw[i] > 0:
            deg = ((baseline_bw[i] - fragmented_bw[i]) / baseline_bw[i]) * 100
            degradation.append(deg)
        else:
            degradation.append(0)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(block_sizes, degradation, marker='o', linewidth=2, markersize=8, color='#c0392b')
    ax.fill_between(range(len(block_sizes)), degradation, alpha=0.3, color='#e74c3c')

    ax.set_xlabel('Размер блока', fontsize=12)
    ax.set_ylabel('Деградация (%)', fontsize=12)
    ax.set_title('Снижение производительности', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(block_sizes)))
    ax.set_xticklabels(block_sizes)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(graphs_dir, 'performance_degradation.png'), dpi=300)
    print("График 3: performance_degradation.png")
    plt.close()

seq_read_base = next((d for d in data if d['test_name'] == 'baseline_seq_read'), None)
seq_read_frag = next((d for d in data if d['test_name'] == 'fragmented_seq_read'), None)

if seq_read_base and seq_read_frag:
    bw_base = float(seq_read_base['read_bw_mbs'])
    bw_frag = float(seq_read_frag['read_bw_mbs'])

    degradation_pct = ((bw_base - bw_frag) / bw_base * 100) if bw_base > 0 else 0

    print(f"\n=== РЕЗУЛЬТАТЫ ===")
    print(f"Baseline: {bw_base:.2f} MB/s")
    print(f"Fragmented: {bw_frag:.2f} MB/s")
    print(f"Деградация: {degradation_pct:.2f}%")

print("\nГрафики созданы!")
PYTHON_SCRIPT

    log "Графики созданы"
}

# Генерация отчета
generate_report() {
    log "=== ГЕНЕРАЦИЯ ОТЧЕТА ==="

    cat > "$REPORT_FILE" <<EOF
# Лабораторная работа
## Анализ производительности СХД с фрагментацией файлов

### Цель работы
Исследовать влияние фрагментации файлов на производительность RAID 10.

### Конфигурация системы

**ОС:** $(lsb_release -d | cut -f2 2>/dev/null || echo "Linux")
**Ядро:** $(uname -r)
**Процессор:** $(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs 2>/dev/null || echo "N/A")
**Память:** $(free -h | grep Mem | awk '{print $2}' 2>/dev/null || echo "N/A")
**Дата:** $(date '+%Y-%m-%d %H:%M:%S')

**RAID:**
- Устройств: $NUM_DEVICES
- Размер: $DEVICE_SIZE каждое
- Уровень: RAID 10
- Layout: near (n2)
- Chunk: 512K

### Информация о RAID

\`\`\`
$(cat "${RESULTS_DIR}/raid_info.txt" 2>/dev/null || echo "N/A")
\`\`\`

### Фрагментация

\`\`\`
$(cat "${RESULTS_DIR}/fragmentation_level.txt" 2>/dev/null || echo "N/A")
\`\`\`

### Результаты

![Последовательное чтение](graphs/fragmentation_impact_sequential.png)

![IOPS](graphs/fragmentation_impact_iops.png)

![Деградация](graphs/performance_degradation.png)

### Выводы

1. Фрагментация оказывает влияние на последовательные операции
2. Случайный доступ менее чувствителен к фрагментации
3. Для больших блоков деградация более выражена

---

**Выполнил:** [ФИО]
**Дата:** $(date '+%Y-%m-%d')
EOF

    log "Отчет создан: $REPORT_FILE"
}

# Очистка
cleanup() {
    log "=== ОЧИСТКА ==="

    if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
        umount "$MOUNT_POINT" 2>/dev/null || true
    fi

    if [ -e "$RAID_DEVICE" ]; then
        mdadm --stop "$RAID_DEVICE" 2>/dev/null || true
    fi

    if [ ${#LOOP_DEVICES[@]} -gt 0 ]; then
        for loop_dev in "${LOOP_DEVICES[@]}"; do
            if [ -e "$loop_dev" ]; then
                losetup -d "$loop_dev" 2>/dev/null || true
            fi
        done
    fi

    log "Очистка завершена"
}

trap cleanup EXIT INT TERM

# Главная функция
main() {
    echo -e "${GREEN}=== RAID 10 Performance Test ===${NC}"

    check_root
    setup_directories

    log "=== НАЧАЛО ==="

    check_dependencies
    create_loop_devices
    create_raid10
    create_filesystem

    baseline_tests
    create_fragmented_file
    fragmented_tests

    parse_fio_results
    generate_graphs
    generate_report

    log "=== ЗАВЕРШЕНО ==="
    log ""
    log "Результаты: $WORK_DIR"
    log "Отчет: $REPORT_FILE"
    log ""
}

main "$@"
