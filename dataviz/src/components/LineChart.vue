<template>
  <div>
    <div class="boundaries">
      {{ chartId }}
    </div>
    <Line
      :key="componentKey"
      :chartData="chartData"
      :chartOptions="chartOptions"
      :chartId="chartId"
      :width="width"
      :height="height"
      :cssClasses="cssClasses"
      :styles="styles"
      :plugins="plugins"
    />
    <div class="boundaries">
      <div>
        min: <input type="number" v-model="y_min">
      </div>
      <div>
        max: <input type="number" v-model="y_max">
      </div>
    </div>
  </div>
</template>

<script>
import zoomPlugin from "chartjs-plugin-zoom";

import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  CategoryScale,
} from "chart.js";

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  CategoryScale,
  zoomPlugin
);

export default {
  name: "LineChart",
  components: {
    Line,
  },
  props: {
    chartId: {
      type: String,
      default: "line-chart",
    },
    width: {
      type: Number,
      default: 400,
    },
    height: {
      type: Number,
      default: 400,
    },
    cssClasses: {
      default: "",
      type: String,
    },
    styles: {
      type: Object,
      default: () => {},
    },
    plugins: {
      type: Array,
      default: () => [],
    },
    labels: {
      type: Array,
      default: () => [],
    },
    datasets: {
      type: Array,
      default: () => [],
    }
  },
  data: function() {
    return {
      y_min: -30,
      y_max: 30,
      componentKey: 0
    }
  },
  computed: {
    chartData() {
      return {
        labels: this.labels,
        datasets: this.datasets,
      };
    },
    chartOptions() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        spanGaps: true,
        scales: {
          y: {
            min: this.y_min,
            max: this.y_max,
          },
          x: {
            display: false
          }
        },
        elements: {
          point: {
            radius: 0,
          },
        },
        plugins: {
          tooltip: {
            enabled: true,
          },
          zoom: {
            zoom: {
              wheel: {
                enabled: false,
              },
              pinch: {
                enabled: false,
              },
              mode: "xy",
            },
          },
        },
      };
    },
  },
  watch: {
    chartOptions: function() {
        this.componentKey += 1;
     },
  },
};
</script>

<style lang="scss" scoped>
.boundaries {
  display: flex;
  justify-content: space-around;
}
</style>
