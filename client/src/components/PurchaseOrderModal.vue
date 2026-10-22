<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">{{ mode === 'create' ? 'Create Purchase Order' : 'Purchase Order' }}</h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-summary">
              <div class="item-name">{{ translateProductName(backlogItem.item_name) }}</div>
              <div class="item-sku">SKU: {{ backlogItem.item_sku }} &middot; Short {{ shortage }} units</div>
            </div>

            <div v-if="error" class="error-message">{{ error }}</div>

            <div v-if="mode === 'view'">
              <div v-if="loading" class="loading">Loading...</div>
              <div v-else-if="po" class="info-grid">
                <div class="info-item"><div class="info-label">PO Number</div><div class="info-value mono">{{ po.id }}</div></div>
                <div class="info-item"><div class="info-label">Status</div><div class="info-value">{{ po.status }}</div></div>
                <div class="info-item"><div class="info-label">Supplier</div><div class="info-value">{{ po.supplier_name }}</div></div>
                <div class="info-item"><div class="info-label">Quantity</div><div class="info-value">{{ po.quantity }} units</div></div>
                <div class="info-item"><div class="info-label">Unit Cost</div><div class="info-value">{{ formatCurrency(po.unit_cost, currentCurrency) }}</div></div>
                <div class="info-item"><div class="info-label">Total</div><div class="info-value">{{ formatCurrency(po.quantity * po.unit_cost, currentCurrency) }}</div></div>
                <div class="info-item"><div class="info-label">Expected Delivery</div><div class="info-value">{{ po.expected_delivery_date }}</div></div>
                <div class="info-item"><div class="info-label">Created</div><div class="info-value">{{ po.created_date }}</div></div>
                <div v-if="po.notes" class="info-item full"><div class="info-label">Notes</div><div class="info-value">{{ po.notes }}</div></div>
              </div>
            </div>

            <form v-else id="po-form" class="po-form" @submit.prevent="submit">
              <label class="field full">
                <span class="info-label">Supplier</span>
                <input v-model.trim="form.supplier_name" required maxlength="200" class="input" />
              </label>
              <label class="field">
                <span class="info-label">Quantity</span>
                <input v-model.number="form.quantity" type="number" min="1" required class="input" />
              </label>
              <label class="field">
                <span class="info-label">Unit Cost (USD)</span>
                <input v-model.number="form.unit_cost" type="number" min="0" step="0.01" required class="input" />
              </label>
              <label class="field full">
                <span class="info-label">Expected Delivery</span>
                <input v-model="form.expected_delivery_date" type="date" :min="today" required class="input" />
              </label>
              <label class="field full">
                <span class="info-label">Notes</span>
                <textarea v-model="form.notes" maxlength="1000" rows="3" class="input"></textarea>
              </label>
            </form>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="close">{{ mode === 'create' ? 'Cancel' : 'Close' }}</button>
            <button v-if="mode === 'create'" type="submit" form="po-form" class="btn-primary" :disabled="loading">
              {{ loading ? 'Creating...' : 'Create PO' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

const { translateProductName, currentCurrency } = useI18n()

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  backlogItem: { type: Object, default: null },
  mode: { type: String, default: 'create' }
})

const emit = defineEmits(['close', 'po-created'])

const today = new Date().toISOString().slice(0, 10)
const form = ref({})
const po = ref(null)
const loading = ref(false)
const error = ref(null)

const shortage = computed(() =>
  props.backlogItem ? props.backlogItem.quantity_needed - props.backlogItem.quantity_available : 0
)

watch(() => props.isOpen, async (open) => {
  if (!open || !props.backlogItem) return
  error.value = null
  po.value = null
  if (props.mode === 'create') {
    form.value = { supplier_name: '', quantity: shortage.value, unit_cost: 0, expected_delivery_date: '', notes: '' }
    return
  }
  loading.value = true
  try {
    po.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
  } catch (err) {
    error.value = 'Failed to load purchase order'
  } finally {
    loading.value = false
  }
})

const submit = async () => {
  loading.value = true
  error.value = null
  try {
    const created = await api.createPurchaseOrder({
      ...form.value,
      backlog_item_id: props.backlogItem.id,
      notes: form.value.notes || null
    })
    emit('po-created', created)
  } catch (err) {
    error.value = err.response?.data?.detail?.toString() || 'Failed to create purchase order'
  } finally {
    loading.value = false
  }
}

const close = () => emit('close')
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  border-radius: 6px;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem;
}

.item-summary {
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 1.5rem;
}

.item-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

.item-sku,
.mono {
  font-size: 0.875rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
}

.error-message {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.loading {
  color: #64748b;
}

.info-grid,
.po-form {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

.info-item,
.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.full {
  grid-column: 1 / -1;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.input {
  padding: 0.625rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.875rem;
  font-family: inherit;
  color: #0f172a;
}

.input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.modal-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  font-family: inherit;
}

.btn-secondary {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #334155;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.btn-primary {
  background: #0f172a;
  border: 1px solid #0f172a;
  color: white;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
