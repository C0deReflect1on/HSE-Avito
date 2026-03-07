#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="http://localhost:8003"

echo -e "${GREEN}🚀 Начинаем нагрузочное тестирование API${NC}\n"

# Функция для создания случайных данных
generate_random_data() {
    local seller_id=$((RANDOM % 1000 + 1))
    local item_id=$((RANDOM % 10000 + 1))
    local is_verified=$((RANDOM % 2))
    local category=$((RANDOM % 100 + 1))
    local images_qty=$((RANDOM % 10 + 1))
    local desc_length=$((RANDOM % 500 + 100))
    
    # Генерация случайного описания
    local description=$(head /dev/urandom | LC_ALL=C tr -dc 'a-zA-Z0-9 ' | head -c $desc_length)
    
    echo "{
        \"seller_id\": $seller_id,
        \"is_verified_seller\": $([ $is_verified -eq 1 ] && echo "true" || echo "false"),
        \"item_id\": $item_id,
        \"name\": \"Test Item $item_id\",
        \"description\": \"$description\",
        \"category\": $category,
        \"images_qty\": $images_qty
    }"
}

# Проверка доступности API
echo -e "${YELLOW}Проверка доступности API...${NC}"
if ! curl -s "$API_URL/" > /dev/null; then
    echo "❌ API недоступен на $API_URL"
    echo "Запусти приложение: uvicorn app.main:app --host 0.0.0.0 --port 8003"
    exit 1
fi
echo -e "${GREEN}✅ API доступен${NC}\n"

# Счетчики
success_count=0
error_count=0
total_requests=100

echo -e "${YELLOW}Отправляем $total_requests запросов к /predict...${NC}\n"

for i in $(seq 1 $total_requests); do
    data=$(generate_random_data)
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/predict" \
        -H "Content-Type: application/json" \
        -d "$data")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" -eq 200 ]; then
        ((success_count++))
        echo -e "${GREEN}✓${NC} Запрос $i/$total_requests - HTTP $http_code"
    else
        ((error_count++))
        echo -e "❌ Запрос $i/$total_requests - HTTP $http_code"
    fi
    
    # Небольшая задержка для имитации реального трафика
    sleep 0.1
done

echo -e "\n${YELLOW}Тестируем разные эндпоинты...${NC}\n"

# Тест root эндпоинта
echo "Тест GET /"
curl -s "$API_URL/" | head -c 100
echo -e "\n"

# Тест метрик
echo "Тест GET /metrics"
curl -s "$API_URL/metrics" | head -n 20
echo -e "...\n"

# Генерация некоторых запросов с разными параметрами для разнообразия метрик
echo -e "\n${YELLOW}Отправляем запросы с разными характеристиками...${NC}\n"

# Верифицированные продавцы
for i in {1..20}; do
    curl -s -X POST "$API_URL/predict" \
        -H "Content-Type: application/json" \
        -d "{
            \"seller_id\": $((RANDOM % 100)),
            \"is_verified_seller\": true,
            \"item_id\": $((RANDOM % 1000)),
            \"name\": \"Premium Item $i\",
            \"description\": \"High quality product from verified seller\",
            \"category\": $((RANDOM % 50)),
            \"images_qty\": $((RANDOM % 5 + 5))
        }" > /dev/null
    echo -e "${GREEN}✓${NC} Верифицированный продавец $i/20"
    sleep 0.05
done

# Неверифицированные продавцы с подозрительным контентом
for i in {1..20}; do
    curl -s -X POST "$API_URL/predict" \
        -H "Content-Type: application/json" \
        -d "{
            \"seller_id\": $((RANDOM % 1000 + 1000)),
            \"is_verified_seller\": false,
            \"item_id\": $((RANDOM % 10000 + 10000)),
            \"name\": \"Cheap Item $i\",
            \"description\": \"Buy now! Special offer! Limited time!\",
            \"category\": $((RANDOM % 100)),
            \"images_qty\": $((RANDOM % 3 + 1))
        }" > /dev/null
    echo -e "${YELLOW}⚠${NC} Неверифицированный продавец $i/20"
    sleep 0.05
done

# Запросы с ошибками (невалидные данные)
echo -e "\n${YELLOW}Генерируем запросы с ошибками...${NC}\n"
for i in {1..10}; do
    curl -s -X POST "$API_URL/predict" \
        -H "Content-Type: application/json" \
        -d "{\"invalid\": \"data\"}" > /dev/null
    echo -e "❌ Невалидный запрос $i/10"
    sleep 0.1
done

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📊 Итоговая статистика${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Успешных запросов: ${GREEN}$success_count${NC}"
echo -e "Ошибок: ${YELLOW}$error_count${NC}"
echo -e "Всего отправлено: $((success_count + error_count + 40 + 10))"
echo -e "\n${YELLOW}🔗 Открой Grafana: http://localhost:3000 (admin/admin)${NC}"
echo -e "${YELLOW}🔗 Prometheus: http://localhost:9090${NC}"
echo -e "${YELLOW}🔗 Метрики API: http://localhost:8003/metrics${NC}"
